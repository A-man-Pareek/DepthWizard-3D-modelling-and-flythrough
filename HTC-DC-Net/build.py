def get_model_and_optimizer(cfgs, test=False):
    if cfgs["model"] in ("htcdc", "HTCDCNet"):
        from htcdc import UBins
        model = UBins(cfgs)
    else:
        raise NotImplementedError(f"Model '{cfgs.get('model')}' is not implemented.")
    if test:
        return model
        
    if cfgs["optimizer"] == "Adam":
        from torch.optim import Adam
        optim = Adam
    elif cfgs["optimizer"] == "SGD":
        from torch.optim import SGD
        optim = SGD
    elif cfgs["optimizer"] == "Nadam":
        from torch.optim import NAdam
        optim = NAdam
    elif cfgs["optimizer"] == "AdamW":
        from torch.optim import AdamW
        optim = AdamW
    else:
        raise NotImplementedError(f"Optimizer '{cfgs.get('optimizer')}' is not implemented.")
    optimizer = optim(filter(lambda x: x.requires_grad, model.parameters()), lr=cfgs["lr"])
    return model, optimizer