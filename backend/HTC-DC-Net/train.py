import torch
import argparse
import wandb
import os
from datetime import datetime
import time
from tqdm import tqdm

from utils import AverageMeter, UpdatableDict, convert_from_string, data_to_device, load_yaml, \
    fix_seed_for_reproducability, save_config
from build import get_model_and_optimizer
from dataloaders import get_train_val_dataloaders

def parse_arguments():
    parser = argparse.ArgumentParser(description='Training configuration')
    parser.add_argument('--config', default=None, help='Specify a config file path')
    parser.add_argument('--exp_config', default=None, help='Specify an experiment config file path')
    parser.add_argument('--restore', action='store_true', help='Restore the run')
    parser.add_argument('--overfit', action='store_true', help='Overfit on small batches for debugging')
    args, unknown_raw = parser.parse_known_args()
    unknown = []
    for ur in unknown_raw:
        unknown.extend(ur.split("="))
    return args, unknown

def train(cfgs, logger, train_dataloader, val_dataloader, model, optimizer, checkpoint_name=None, scheduler=None):
    patience = cfgs.get("patience", cfgs["max_epochs"])
    curr_patience = 0
    metric_names = cfgs.get("early_stopping", None)
    metric_modes = cfgs.get("early_stopping_mode", ['max'])
    
    early_stopping = False
    if metric_names is not None:
        early_stopping = True
        best_metric_init = {}
        for metric_name, metric_mode in zip(metric_names, metric_modes):
            if metric_mode == "max":
                best_metric_init[metric_name] = -999
            else:
                best_metric_init[metric_name] = 999
    
    if cfgs["restore"]:
        chkpt_name = checkpoint_name if checkpoint_name is not None else 'checkpoint_last.pth.tar'
        chkpt_file = os.path.join(cfgs["experiment_dir"], chkpt_name)
        if not os.path.exists(chkpt_file):
            candidate_paths = [
                os.path.join(r"C:\Users\Aman\Desktop\SIHfinal\backend\checkpoints", chkpt_name),
                os.path.join(r"C:\Users\Aman\Desktop\SIHfinal\backend\HTC-DC-Net\checkpoints", chkpt_name),
            ]
            for c_path in candidate_paths:
                if os.path.exists(c_path):
                    chkpt_file = c_path
                    break

        if os.path.exists(chkpt_file):
            print(f"Loading weights from checkpoint: {chkpt_file}")
            chkpt = torch.load(chkpt_file, map_location="cpu")
            global_step = chkpt["step"]
            start_epoch = chkpt["epoch"]
            print(f"Resuming training starting at Epoch {start_epoch + 1} (global step {global_step})...")
            model.load_state_dict(chkpt["state_dict"])
            if "optimizer" in chkpt and chkpt["optimizer"]:
                try:
                    optimizer.load_state_dict(chkpt["optimizer"])
                except Exception as e:
                    print(f"Warning: Could not restore optimizer state: {e}")
            if cfgs.get("early_stopping", None) is not None:
                curr_patience = chkpt.get("patience", 0)
                best_metric = chkpt.get("best_metric", best_metric_init)
        else:
            global_step = 0
            start_epoch = 0
            if cfgs["early_stopping"] is not None:
                best_metric = best_metric_init
                curr_patience = 0
    else:
        global_step = 0
        start_epoch = 0
        if cfgs["early_stopping"] is not None:
            best_metric = best_metric_init
            curr_patience = 0
    if curr_patience == patience:
        return

    for epoch in range(start_epoch, cfgs["max_epochs"]):
        model.train()
        loss_train = AverageMeter()
        for _, image, gt in tqdm(train_dataloader, desc=f"Epoch {epoch+1}: training ..."):
            global_step += 1
            log_flag = (global_step % cfgs["log_interval"] == 0)

            image = data_to_device(image, device=cfgs["device"])
            gt = data_to_device(gt, device=cfgs["device"])
            losses, pred = model(image, gt)
            loss_total = losses["loss_total"]
            loss_train.update(loss_total.item(), len(image))

            optimizer.zero_grad()
            loss_total.backward()
            #torch.nn.utils.clip_grad_norm_([layer.parameters() for layer in model.model.adaptive_bins_layer.patch_transformer.transformer_encoder.layers], 0.02)
            #torch.nn.utils.clip_grad_norm_(model.model.adaptive_bins_layer.patch_transformer.transformer_encoder.parameters(), 0.002)
            optimizer.step()
            
            '''
            for name, grad in zip(
                    ['conv_out.weight', 'conv_out.bias', 'regressor.last.weight', 'regressor.last.bias'],
                    [model.model.conv_out[0].weight.grad, model.model.conv_out[0].bias.grad, model.model.adaptive_bins_layer.regressor[4].weight.grad, model.model.adaptive_bins_layer.regressor[4].bias]):
                print(name, grad.min(), grad.max())
            '''
            
            if (cfgs.get("lr_policy", "constant") != "reduceonplateau") & (scheduler is not None):
                scheduler.step()

            if log_flag:
                log_dict = {
                    'step': global_step,
                    'epoch': epoch
                }
                log_dict.update({'train/'+key: loss for key, loss in losses.items()})
                if scheduler:
                    log_dict.update({'lr': float(optimizer.param_groups[0]['lr'])})
                log_dict.update(model.vis(image, pred, gt))
                logger.log(log_dict)
        logger.log({
            'epoch': epoch,
            'train/loss_avg': loss_train.avg
        })

        model.eval()
        loss_val = AverageMeter()
        eval_dict = UpdatableDict()
        skip_flag = False
        with torch.no_grad():
            for _, image, gt in tqdm(val_dataloader, desc=f"Epoch {epoch+1}: validating ..."):
                tic = time.perf_counter()

                image = data_to_device(image, device=cfgs["device"])
                gt = data_to_device(gt, device=cfgs["device"])
                losses, pred, eval_params = model(image, gt)
                if not cfgs.get("rcnn", False):
                    loss_val.update(losses["loss_total"].item(), len(image))
                eval_dict.update(eval_params)
                toc = time.perf_counter()
                if toc - tic > 10:
                    print(f"Epoch {epoch+1}: validation takes too long, skipping ...")
                    skip_flag = True
                    break
        save_dict = {
            'step': global_step,
            'epoch': epoch + 1,
            'state_dict': model.state_dict(),
            'optimizer': optimizer.state_dict(),
        }
        if scheduler:
            save_dict.update({'scheduler': scheduler.state_dict()})
        log_dict = {'epoch': epoch}
        if not cfgs.get("rcnn", False):
            log_dict.update({'val/loss_total': loss_val.avg})
        log_dict.update(model.vis(image, pred, gt, True))
        if (not skip_flag) & early_stopping:
            eval_res = model.evaluate(eval_dict())
            log_dict.update(eval_res)
            no_stop_flag = []
            for metric_name, metric_mode in zip(metric_names, metric_modes):
                if ((metric_mode == 'max') & (log_dict[metric_name] > best_metric[metric_name])) | \
                ((metric_mode == 'min') & (log_dict[metric_name] < best_metric[metric_name])):
                    best_metric[metric_name] = log_dict[metric_name]
                    no_stop_flag.append(True)
                    curr_patience = 0
                else:
                    no_stop_flag.append(False)
            
            if (cfgs.get("lr_policy", "constant") == "reduceonplateau") & (scheduler is not None):
                scheduler.step(eval_res["rmse"])

            if not any(no_stop_flag):
                curr_patience += 1
            else:
                save_dict.update({
                    'best_metric': best_metric,
                })
                for metric_name, no_stop in zip(metric_names, no_stop_flag):
                    if no_stop:
                        if '/' in metric_name:
                            metric_name = metric_name.split('/')[-1]
                        torch.save(save_dict, os.path.join(cfgs["experiment_dir"], 'checkpoint_best_{:s}.pth.tar'.format(metric_name)))
        save_dict.update({
            "patience": curr_patience
        })
        logger.log(log_dict)
        
        if (epoch % cfgs["checkpoint_interval"]) == 0:
            torch.save(save_dict, os.path.join(cfgs["experiment_dir"], 'checkpoint_{:03d}.pth.tar'.format(epoch))) 
        
        torch.save(save_dict, os.path.join(cfgs["experiment_dir"], 'checkpoint_last.pth.tar'))

        if (not skip_flag) & early_stopping & (curr_patience == patience):
            print(f"Epoch {epoch+1}: maximum patience reached, early stopping ...")
            break

def main():
    args, unknown = parse_arguments()
    cfgs = {}

    if not args.restore:
        if args.config is None or not os.path.isfile(args.config):
            raise ValueError("Config file --config must be specified and exist (e.g. --config configs/htcdc.yaml)")

        cfgs = load_yaml(args.config)
        if args.exp_config and os.path.isfile(args.exp_config):
            cfgs.update(load_yaml(args.exp_config))
        elif os.path.isfile("configs/configs1.yaml"):
            cfgs.update(load_yaml("configs/configs1.yaml"))

        cfgs["restore"] = False
        cfgs["overfit"] = args.overfit
        checkpoint_base = cfgs.get("checkpoint_dir", "checkpoints")
        model_name = cfgs.get("model", "htcdc")
        cfgs["checkpoint_dir"] = os.path.join(checkpoint_base, model_name)
        cfgs["experiment_dir"] = os.path.join(cfgs["checkpoint_dir"], datetime.now().strftime('%y%m%d_%H%M%S'))

        if cfgs.get("overfit", False):
            cfgs["log_interval"] = 1
            cfgs["checkpoint_interval"] = cfgs.get("max_epochs", 20)
            cfgs["batch_size"] = 1
            cfgs["patience"] = cfgs.get("max_epochs", 20)
        
        print(f"Starting training from {args.config}...")

    else:
        if args.exp_config and os.path.isfile(args.exp_config):
            cfgs = load_yaml(args.exp_config)
        else:
            config_file = args.config if (args.config and os.path.isfile(args.config)) else "configs/htcdc.yaml"
            cfgs = load_yaml(config_file)
            if os.path.isfile("configs/configs1.yaml"):
                cfgs.update(load_yaml("configs/configs1.yaml"))

        cfgs['restore'] = True
        cfgs['overfit'] = args.overfit
        if "checkpoint_dir" not in cfgs:
            cfgs["checkpoint_dir"] = os.path.join("checkpoints", cfgs.get("model", "htcdc"))
        if "experiment_dir" not in cfgs:
            cfgs["experiment_dir"] = cfgs["checkpoint_dir"]
        os.makedirs(cfgs["experiment_dir"], exist_ok=True)
        print("Restoring training from epoch 7 checkpoint...")

    if unknown:
        assert (len(unknown)%2==0), "Misc variables should be in pairs, key and value"
        for key, value in zip(unknown[0::2], unknown[1::2]):
            cfgs[key] = convert_from_string(value)
    
    
    project = cfgs.get("project", 'HTCDC')
    runname = cfgs.get("name", None)
    wandb_id = cfgs.get("wandb_run_id", None)
    
    if cfgs.get("restore", False) and wandb_id:
        try:
            logger = wandb.init(project=project, id=wandb_id, resume='allow')
        except Exception:
            logger = wandb.init(project=project, name=runname)
    else:
        logger = wandb.init(project=project, name=runname)

    cfgs["wandb_run_id"] = getattr(logger, "id", None)

    print(cfgs)
    save_config(cfgs, os.path.join(cfgs["experiment_dir"], 'config.yaml'))
    logger.config.update(cfgs, allow_val_change=True)
    seed = cfgs.get("seed", 42)
    fix_seed_for_reproducability(seed)

    train_loader, val_loader = get_train_val_dataloaders(cfgs)
    model, optimizer = get_model_and_optimizer(cfgs)
    model.to(cfgs["device"])
    logger.watch(model)
    train(cfgs, logger, train_loader, val_loader, model, optimizer)


if __name__ == "__main__":
    main()
