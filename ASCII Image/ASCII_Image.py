from tkinter import Y
from PIL import Image
import sys
import os
import numpy as np

#String of all ASCII characters used to change brightness based on how 'full' of text the space is. Ordered dark to bright.
ASCIIString = "`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
f = 255/(len(ASCIIString)-1) #break a 256-bit brightness into discrete steps based on length of ASCII string.


def Colourise(r,g,b):
    """Takes RGB values, calculates a brightness value and returns the appropriate ASCII character
    Includes a colour-formatting string infront of the ASCII character to add colour to the console"""
    Bright = int(((r+g+b)/3)/f)
    escape = '\033[38;2;' + str(r) + ';' + str(g) + ';' + str(b) + 'm'
    return escape + (ASCIIString[Bright]*3)


def BnWise(r,g,b):
    """Takes an RGB value and returns a default coloured character based on the brightness value."""
    Bright = int((((r*0.21) + (g*0.72) + (b*0.07)))/f) #Calculate brightness based on human colour perception weights.
    return ASCIIString[Bright]*3

def Main():
    coloured = input("Coloured? Y=Color N=B&W: >")

    #Permanently set the desired function now, so that the if statement doesn't have to run x million times.
    if coloured == "Y" or coloured == "y":
        func = Colourise
    else:
        func = BnWise

    im = Image.open(os.path.join(sys.path[0], "landscape.jpg")) #Open the image as RGB array.
    #print("Image Details:", im.format, im.size, im.mode) #Print the format details for the user to check.

    #Convert the image to a numpy array.
    PixelArray = np.asarray(im)

    for i in PixelArray:    #For each row
        out = ""                #Create a blank string to add pixel info to.
        for j in i:             #For each pixel
            out += func(j[0],j[1],j[2]) #For each pixel, calculate the ASCII character (and any colour formatting)

        print(out)              #Print the row.
    
    end = input("Finished?")    #Keep the image displated until the user is done.


if __name__ == "__main__":
    Main()





