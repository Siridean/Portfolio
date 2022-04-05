from itertools import chain
import numpy as np
from PIL import Image
import glob
import os
import sys
from tqdm import tqdm
import multiprocessing as mult
vipshome = 'C:/vips-dev-8.12/bin'
os.environ['PATH'] = vipshome + ';' + os.environ['PATH']
import pyvips

def main(): 
    """main function to load the image, call required functions and save the output."""
    f = 5 #image reduction factor. MIN=11 for old phone pic and sz at 170
    sz:int = 25 #source image size (width)

    inputIm = Image.open(os.path.join(sys.path[0], "Primary_Image.jpg"))
    inputIm = inputIm.reduce(f) #Pixelate input image.
    w = inputIm.width
    h = inputIm.height
    inputArray = np.asarray(inputIm, dtype=np.uint8)
    

    sources = SortSorce(os.path.join(sys.path[0], "Sources/*.jpg"), sz) #load, average and sort the source (collaging) images.

    CreateImage(inputArray, sources, w, h, sz) #swap each pixel for a source image and assign the output.




def AddImage(data:tuple) -> np.ndarray:
    """Squares and reduces a source image to size sz*sz pixels,
    converts it to an numpy.ndarray"""
    im = data[0]
    sz = data[1]

    sIm = Image.open(im)
    halfSpan = min(sIm.height, sIm.width)/2             #Get half the smallest of height/width of image
    upper = (sIm.height/2) - halfSpan                   #Top Left most co-ord is (0,0)
    lower = (sIm.height/2) + halfSpan
    left = (sIm.width/2) - halfSpan
    right = (sIm.width/2) + halfSpan
    sIm = sIm.crop((left,upper,right,lower))            #crop image to make it square
    sIm.thumbnail((sz,sz))                              #reduce image size to sz*sz pixels

    rgbArray = np.asarray(sIm, dtype=np.uint8)          #Convert to colour image Array
    OutBW = RGBtoGrey(rgbArray, sz)                     #Convert to RGB array to greyscale Array, with average RGB vals
    OutRGB = AvgRGB(rgbArray, sz)                       #Get average RGB values for color array

    return (OutRGB, OutBW)                              #returns a tuple of ((R,G,B, Colour-pixelarray),(R,G,B, bw-Pixelarray))


def AvgRGB(source:np.ndarray, sz:int) -> tuple:
    """finds the average RGB value of a source image,
    returns it along with the pixel array"""

    r,g,b= 0,0,0
    for row in source:
        for pixel in row:
            r += pixel[0]
            g += pixel[1]
            b += pixel[2]

    r = int(r/(sz**2))
    g = int(g/(sz**2))
    b = int(b/(sz**2))

    return (r,g,b, source)  #returns a tuple of (R,G,B, pixelArray)


def RGBtoGrey(source:np.ndarray, sz:int) -> tuple:
    """Converts a source pixelArray from RGB to RGB-Greyscale. 
    Returns average RGB value and converted pixelArray in a tuple
    (R,G,B, pixelArray)"""
    
    gArray = np.dot(source[...,:3], [0.2989, 0.5870, 0.1140])
    out = np.zeros((sz,sz,3),dtype=np.uint8)
    Gr = 0
    for rdx in range(sz):
        for pdx in range(sz):
            temp = np.uint8(gArray[rdx,pdx])
            Gr += temp
            for i in range(3):
                out[rdx,pdx,i] = temp
    
    r=g=b = int(Gr/sz**2)

    return (r,g,b, out)


    #Conv = np.full([sz,sz, 3], [0.2989, 0.5870, 0.1140])
    #return np.multiply(source, Conv)



def SortSorce(FolderPath, sz:int) -> list:
    """Loads all the images from the folder path, 
    calculates their average overall RGB values,
    saves the output into a sorted (Hi-Lo, RGB) dictionary of {average(R,G,B) : pixelArray}"""
    
    print("Sorting and storing source images...")
    sourceFolder = glob.glob(FolderPath)
    SourceArray = [[[None]*256]*256]*256 #Create blank RGB space
    
    wPool = mult.Pool(mult.cpu_count()-1)
    tasks = [(im, sz) for im in sourceFolder]
    for tup in tqdm(wPool.imap(AddImage, tasks, 50),total=len(sourceFolder)):   #Returns avgRGB (r,g,b, pixelarray) for each source image
        for sc in tup:
            SourceArray[sc[0]][sc[1]][sc[2]] = sc[3]    #Fill RGB space with pixel arrays at the corresponding RGB co-ordinate

    print("Sources sorted and stored.")
    print("")
    return SourceArray


def FindNearest(data:tuple) -> tuple:
    """Takes the input RGB values & compares them to the source images,
    returns the avg RGB value of the source image with the closest RGB match"""
    r,g,b = int(data[2][0]), int(data[2][1]), int(data[2][2])
    sources = data[3]
    found = False
    d = 0
    while not found:
    
        #Find current ranges and bound by 0,255 min,max.
        rRC= np.clip(range(r-d+1, r+d), 0, 255) #Current Range for RED with ends clipped by 1
        rR = np.clip(range(r-d, r+d+1), 0, 255) #Current Range for RED.
        gR = np.clip(range(g-d, g+d+1), 0, 255) #current Range for GREEN.
        bR = np.clip(range(b-d, b+d+1), 0, 255) #current Range for BLUE.

        rF = np.clip((r+d, r-d), 0, 255) #MAX and MIN for RED at current cube radius.
        gF = np.clip((g+d, g-d), 0, 255) #MAX and MIN for GREEN at current cube radius.
        bF = np.clip((b+d, b-d), 0, 255) #MAX and MIN for BLUE at current cube radius.


        #Create a cube-surface in RGB space to search for source image matches.
        #Expands with 'd' after each unsuccessful search.
        searchSpace =   (                                   #Clip value and ranges to 0-255 (RGB range).
                        (rF , gR, bR),     #Top and bottom surface of cube.
                        (rRC, gR, bF),     #2 sides (minus top and bottom rows).
                        (rRC, gF, bR)      #2 sides (minus top and bottom rows).
                        )

        for surface in searchSpace:
            for sR in surface[0]:
                for sG in surface[1]:
                    for sB in surface[2]:
                        if type(sources[sR][sG][sB]) == np.ndarray: #If a source image is in the search-cube
                            found = True
                            return (data[0], data[1], sR, sG, sB)

        d+=1 #Increase the search-cube size



def FindNearestWeighted(data:tuple) -> tuple:
    """Takes the input RGB values & compares them to the source images,
    returns the avg RGB value of the source image with the closest RGB match"""
    r,g,b = int(data[2][0]), int(data[2][1]), int(data[2][2])
    sources = data[3]
    found = False
    dR, dG, dB = 0, 0, 0
    incR, incG, incB = 0, 0, 0
    while not found:
    
        #Find current ranges and bound by 0,255 min,max.
        rRC= np.clip(range(r-dR+incR, r+dR-incR+1), 0, 255) #Current Range for RED with ends clipped by increment
        #rR = np.clip(range(r-dR, r+dR+1), 0, 255) #Current Range for RED.
        gR = np.clip(range(g-dG, g+dG+1), 0, 255) #current Range for GREEN.
        bR = np.clip(range(b-dB, b+dB+1), 0, 255) #current Range for BLUE.

        rMax = np.clip(range(r+dR-incR, r+dR+1), 0, 255)    #MAX new space for RED at current cube radius.
        rMin = np.clip(range(r-dR, r-dR+incR+1), 0 ,255)    #MIN new space for RED at current cube radius.
        rF = chain(rMin, rMax)
        gMax = np.clip(range(g+dG-incG, g+dG+1), 0, 255) 
        gMin = np.clip(range(g-dG, g-dG+incG+1), 0 ,255) 
        gF = chain(gMin, gMax)                              #MAX and MIN for GREEN at current cube radius.
        bMax = np.clip(range(b+dB-incB, b+dB+1), 0, 255) 
        bMin = np.clip(range(b-dB, b-dB+incB+1), 0 ,255) 
        bF = chain(bMin, bMax)                              #MAX and MIN for BLUE at current cube radius.


        #Create a cube-surface in RGB space to search for source image matches.
        #Expands with 'd' after each unsuccessful search.
        searchSpace =   (                                   #Clip value and ranges to 0-255 (RGB range).
                        (rF , gR, bR),     #Top and bottom surface of cube.
                        (rRC, gR, bF),     #2 sides (minus top and bottom rows).
                        (rRC, gF, bR)      #2 sides (minus top and bottom rows).
                        )

        for surface in searchSpace:
            for sR in surface[0]:
                for sG in surface[1]:
                    for sB in surface[2]:
                        if type(sources[sR][sG][sB]) == np.ndarray: #If a source image is in the search-cube
                            found = True
                            return (data[0], data[1], sR, sG, sB)

        #Increase the search-cube size
        incR, incG, incB = int(12/((2 + r)/256)), int(12/4), 3 #int(12/(2 + ((255-r)/256)))
        dR += incR
        dG += incG
        dB += incB


def FindNearestRatio(data:tuple) -> tuple:
    """Takes the input RGB values & compares them to the source images,
    returns the avg RGB value of the source image with the closest RGB match
    searches the source-matrix by casting a line of width 'ratioWidth' from the starting (R,G,B) value."""
    r,g,b = int(data[2][0]), int(data[2][1]), int(data[2][2])
    sources = data[3]
    width = data[4]


    #Create the step vector (largest value = 1), and set the forward and backward moving coordinates to rgb origin.
    rgbMax = max(r,g,b)
    stepVector = np.asarray((r/rgbMax, g/rgbMax, b/rgbMax), dtype=np.float64)
    coordFor = np.asarray((r,g,b), dtype=np.float64)
    coordBack = coordFor

    #Find the two components that will advance more slowly - these will constitue the width and will be search width spaces each time.
    maxIndex = (r,g,b).index(rgbMax)
    widthRange = [i for i in range(3) if i!=maxIndex]

    found = False
    count = 0
    while not found:
        #Empty the search space
        searchSpace = []

        #Advance the coordinates along the step vector
        coordFor += stepVector
        coordBack -+ stepVector
        coordFI = coordFor.astype(np.uint8)
        coordBI = coordBack.astype(np.uint8)
        searchSpace.append(coordFI)
        searchSpace.append(coordBI)

        widthMax = max(width, count)
        for idx in widthRange:
            for w in range(widthMax):
                for i in [-1, 1]:
                    coordFW = coordFI
                    coordFW[idx] += (w*i)
                    coordBW = coordBI
                    coordBW[idx] += (w*i)
                    searchSpace.append(coordFW)
                    searchSpace.append(coordBW)

        for coord in searchSpace:
            sR, sG, sB = coord[0], coord[1], coord[2]
            if type(sources[sR][sG][sB]) == np.ndarray: #If a source image is at the current search coordinate:
                found = True
                return (data[0], data[1], sR, sG, sB)
        
        count += 1 #increase count - used to determine how wide to search (don't want to search wider than long for first few locations)

        

def CreateImage(inputArray:np.ndarray, sources:list, w:int, h:int, sz:int):
    """Takes the reduced input image,
    replaces each pixel with an image from source image based on RGB values
    outputs a new collage Image"""
    print("Converting image to collage of sources...")
    arrayOut = np.zeros((h*sz,w*sz,3),np.uint8)
    
    wPool = mult.Pool(mult.cpu_count()-1)
    tasks = [(idx, jdx, j, sources) for idx,i in enumerate(inputArray) for jdx,j in enumerate(i)] 

    for loc in (tqdm(wPool.imap(FindNearestWeighted, tasks, w), total=h*w)): #Find the nearest source image for each (reduced) input image pixel.
        y,x   = loc[0]*sz, loc[1]*sz
        r,g,b = loc[2], loc[3], loc[4]
        arrayOut[y:y+sz,x:x+sz] = sources[r][g][b] #Write the source image pixels to the output pixel array


    del sources     #Clear sources from memory.
    #Reshape the numpy array to be 1D stream of data - pass that to pyvips to create an image.
    imageOut = pyvips.Image.new_from_memory(arrayOut.reshape(w*sz*h*sz*3).data, width=w*sz, height=h*sz, bands=3, format="uchar")
    del arrayOut    #Clear array from memory since image now exists.
    print("Collaged image created.")


 
    print("Saving image...")
    imageOut.write_to_file(os.path.join(sys.path[0], "Collage.jpg"))
    print("Image saved as", os.path.join(sys.path[0], "Collage.jpg")) 
        


if __name__ == "__main__":
    from pstats import Stats
    import cProfile

    pr = cProfile.Profile()
    pr.enable()
    main()
    pr.disable()
    stats = Stats(pr)
    stats.sort_stats('cumtime').print_stats(20)






