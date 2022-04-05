import numpy as np
import time

def Main():
    #Set the height and width of the 'play area' in console characters
    h = 54  
    w = 208
    
    BoardState = CreateState(h,w)   #Initialise the board.
    Render(BoardState)      #Dispaly the board in the console
    while True:
        #time.sleep(1/60) #Alter this line to control flickering, based on trial and error of the users device.
        BoardState = NextState(BoardState) #Advance the board to the next state.
        Render(BoardState) #Display the next state.
    

def FindNeighbours(idx:tuple, BoardState:np.ndarray) -> int:
    """Find all neihgbours of the current cell, return the number of neighbours."""
    #Get the coordinates of the current cell
    id = idx[0]
    jd = idx[1]
    count = 0   #Initialise the output.

    #Check each neihgbouring cell (including diagonals, not including itself for another 'alive' cell.)
    for i in range(-1,2):
        for j in range(-1,2):
            if i==0 and j==0:
                continue
            try:
                #If cell found, add to count, otherwise do nothing. If index error, we're at edge of board, do nothing with out of bounds spaces.
                count += BoardState[id+i,jd+j] if (jd+j>=0) and (id+i>=0) else 0
            except IndexError:
                pass
    return count

def Render(BoardState:np.ndarray):
    """Display the current board state in the terminal"""
    sz = np.size(BoardState,1)+2 #Get width of board +2
    print("_"*sz) #Print the upper boundary of the board.
    for row in BoardState:
        RendStr = "|" #Print the left boundary.
        for cell in row:
            RendStr += '#' if cell else ' ' #Print the contents (#=cell, ' '=empty)
        print(RendStr,"|", sep="")      #Print the left boundary, row content, and right boundary.
    print("-"*sz) #Print the lower boundary of the board.

def CreateState(h:int, w:int) -> np.ndarray:
    """Create an initial randomised state of the board"""
    return np.random.randint(0,2,(h,w))

def NextState(BoardState:np.ndarray) ->np.ndarray:
    """Update the state of the board, based on the number of neighbours a cell has.
    A cell may die if not enoguh neighbours, or too many neighbours.
    A dead cell may be revived if it has just the right amount of neighbours."""

    #Create a new blank board, to be updated within this fucntion.
    NewState = np.zeros((np.size(BoardState,0), np.size(BoardState,1)), np.int8)
    for idx, cell in np.ndenumerate(BoardState): #for each cell in the board.
        n = FindNeighbours(idx, BoardState) #get the number of adjacent cells
        if cell:
            NewState[idx] = 0 if (n<2 or n>3) else 1 #Kill if n<2 or n>3. else remain Alive.
        elif (n==3): NewState[idx] = 1 #If was dead, and neighbours =3, revive cell.
    return NewState
        
        



if __name__ == "__main__":
    Main()