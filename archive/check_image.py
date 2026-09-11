from PIL import Image

path = "input/image.png"

image = Image.open(path)

print("Image size:", image.size)
print("Mode:", image.mode)