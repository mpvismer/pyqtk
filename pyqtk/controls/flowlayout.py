'''
The MIT License (MIT)

Copyright (c) 2015 Mark Vismer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import os
import sys
path = os.path.realpath(os.path.abspath(os.path.join(__file__,'../..')))
sys.path.append(path)

import collections
import time
from PyQt4 import QtCore, QtGui

ColumnWise = 1
RowWise = 2

CACHE_LENGTH = 5



class FlowLayout(QtGui.QLayout):
    '''
    Handles automatically repositioning widgets so as to fill up the
    available space.
    '''
	
    def __init__(self, parent=None, margin=None, horizontalSpacing=20, verticalSpacing=3):
        super(FlowLayout, self).__init__(parent)

        if margin is not None:
            self.setContentsMargins(*[margin]*4)

        self.setSpacing(-1)

        self.itemList = []
        
        #TODO: Currently only QtCore.Qt.Vertical is supported
        self.expandDirection = QtCore.Qt.Vertical

        self.fillDirection = ColumnWise
        
        self.horizontalSpacing = horizontalSpacing
        self.verticalSpacing = verticalSpacing
        
        self.colsHist = collections.OrderedDict()
        

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)
        self.colsHist = {}

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return self.expandDirection

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._handleLayout(QtCore.QRect(0, 0, width, 0), False)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._handleLayout(rect, True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()

        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())

        margins = self.getContentsMargins()
        size += QtCore.QSize(margins[0]+margins[2], margins[1]+margins[3])
        return size

###############################################################################
#-Private function implementations
###############################################################################

    def _handleLayout(self, rect, positionItems):
        '''
        Calls the appropriate layout algorithm for the layout configuration.
        '''
        if QtCore.Qt.Vertical==self.expandDirection:
            if ColumnWise == self.fillDirection:
                return self._doVertColumnWise(rect, positionItems)
            elif RowWise == self.fillDirection:
                return self._doVertRowWise(rect, positionItems)
            else:
                raise Exception('Fill direction not supported.')
        else:
            raise Exception('Expand direction not supported.')

			
    def _findMaxWidth(self, fromIdx):
        maxWidth = 0;
        for idx in range(fromIdx, len(self.itemList)):
            size = self.itemList[idx].sizeHint()
            maxWidth = max(maxWidth, size.width())
        return maxWidth


    def _columnStats(self, items):
        maxWidth = 0
        height = - self.verticalSpacing
        for item in items:
            size = item.sizeHint()
            height += size.height() + self.verticalSpacing
            maxWidth = max(maxWidth, size.width())
        return maxWidth, height  
     

    def _findOptimumVertColumnWise(self, widthAllocated):
        '''
        Recursively tries to find the optimum item arrangement with controls
        stacked in column wise, top to bottom, left to right.
        '''
        width, newHeight = self._columnStats(self.itemList)
        bestHeight = 999999999;
        newSolution = [ list(self.itemList) ] 
        while newHeight < bestHeight:
            bestHeight = newHeight
            currentSolution = newSolution
            newSolution = [ list(col) for col in currentSolution]
            widthRemaining = widthAllocated + self.horizontalSpacing
            for idx in range(0, len(newSolution)): 
                width, height = self._columnStats(newSolution[idx])
                widthRemaining -= (width + self.horizontalSpacing)
                if height>=bestHeight:
                    bestHeight = height
                    fromCol = newSolution[idx]
                    if idx == len(newSolution)-1:
                        toCol = []
                        newSolution.append(toCol)
                    else:
                        toCol = newSolution[idx+1]
                    toColIdx = idx+1

            widthFrom, heightFrom = self._columnStats(fromCol)
            widthTo, heightTo = self._columnStats(toCol)
            widthRemaining += (widthFrom + widthTo)    
            widthFrom =  9999999999
            while widthTo + widthFrom > widthRemaining:
                if len(fromCol)>1:
                    toCol.insert(0, fromCol.pop(-1))
                    widthTo, heightTo = self._columnStats(toCol)                
                    widthFrom, heightFrom = self._columnStats(fromCol)
                    if heightTo>bestHeight:
                        fromCol = toCol
                        if toColIdx >= len(newSolution)-1: 
                            toCol = []
                            newSolution.append(toCol)
                        else:
                            toCol = newSolution[toColIdx+1]
                        toColIdx += 1
                        widthRemaining -= widthFrom
                        widthTo, heightTo = self._columnStats(toCol)
                        widthRemaining += widthTo
                        widthFrom =  9999999999
                    else:
                        newHeight = heightFrom
                else:
                    newHeight = bestHeight
                    break
                
        #convert to format
        bestCols = []
        totalWidth = -self.horizontalSpacing;
        maxHeight = 0;
        for col in currentSolution:
            width, height = self._columnStats(col)
            assert (len(col)>0)
            totalWidth += width + self.horizontalSpacing
            maxHeight = max(height, maxHeight)
            bestCols.append((col, width, height))
            
        return bestCols, totalWidth, maxHeight
        

    def _doVertColumnWise(self, rect, positionItems):
        '''
        Stacks controls in columns from top to bottom, left to right.
        '''
        margins = self.getContentsMargins()
        
        allocWidth = rect.width()
                               
        if not (self.colsHist.has_key(allocWidth)):  
            #print('Laying> width:%s,  positionItems:%s' % (rect.width(), positionItems) )
            (cols, totalWidth, maxHeight) = self._findOptimumVertColumnWise(allocWidth - margins[0] - margins[2])
            if len(self.colsHist) >= CACHE_LENGTH:
                self.colsHist.pop(self.colsHist.keys()[0])                
            if len(self.colsHist) < CACHE_LENGTH:
                self.colsHist[allocWidth] = (cols, totalWidth, maxHeight)           
        else:
            (cols, totalWidth, maxHeight) = self.colsHist.pop(allocWidth)
            self.colsHist[allocWidth] = (cols, totalWidth, maxHeight)
            
            
        if positionItems:            
            #print('Positioning...')
            
            totalWidth += margins[0]  +  margins[2]
            if allocWidth > totalWidth:
                remainder = allocWidth - totalWidth
                alignmentSpacing = float(remainder)/(1 + len(cols))
            else:
                alignmentSpacing = 0

            x = rect.x() + margins[0]
            for idx, (col, width, height) in enumerate(cols):
                y = rect.y() + margins[1]
                for item in col:
                    size = item.sizeHint()
                    assert width >= size.width()
                    posx = x + width - size.width() + int(alignmentSpacing*(idx+1))
                    item.setGeometry(QtCore.QRect(QtCore.QPoint(posx, y), size))
                    y += self.verticalSpacing + size.height()
                    #assert y <= height - margins[1]
                x += width + self.horizontalSpacing
        return maxHeight + margins[1] + margins[3]
        
     

    def _doVertRowWise(self, rect, positionItems):
        '''
        Stacks controls from left to right and adds new rows and creates more 
        height as needed.
        '''
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            spaceX = self.horizontalSpacing + wid.style().layoutSpacing(QtGui.QSizePolicy.PushButton, QtGui.QSizePolicy.PushButton, QtCore.Qt.Horizontal)
            spaceY = self.verticalSpacing + wid.style().layoutSpacing(QtGui.QSizePolicy.PushButton, QtGui.QSizePolicy.PushButton, QtCore.Qt.Vertical)
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if positionItems:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()




