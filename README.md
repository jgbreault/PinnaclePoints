# PinnaclePoints
The "superiority" of a point is defined as the point's elevation minus the maximum elevation that can be seen in a direct line of sight from the point. A point with a positive superiority is refered to as a Pinnacle Point.

**Current Algorithm:**

I break the complete dataset of all global summits into chunks for different regions based on latitude and longitude. I currently use 74 chunks: one for each pole defined by above 60 lat and below -60 lat, and one for each 5 lng strip in between. During this data set process, I convert feet to metres, and I add a column for horizon distance defined by sqrt(2*R_earth*prominence). I add some overlap to these regions, ensuring the overlap is at least equal to the maximum horizon distance in the dataset.

0 - Set candidate pinnacle point list (PPc) to be the list of all summits

1 - While PPc isn't empty: (gotta check all candidates):

1.0 - Find highest elevation point in PPc (currentPPc)

1.1 - Find currentPPc's chunk

1.2 - Find the distance between currentPPc and each point in the chunk

1.3 - Find all points within currentPPc's horizon distance and remove from PPc

1.4 - Find all points in the chunk that are both of a higher elevation than currentPPc, and have a horizon distance greater than the distance to currentPPc

1.5 - If no points meet the criteria in 1.4: (Check if this is a pinnacle point)

1.6.0 - Add currentPPc to list of found pinnacle points


**Planned Algorithm:**

Use more chunks. Define a smaller top and bottom, and for the rest use 1-lat-1-lng squares. Ensure the overlap for each chunk is the minimum needed based on the summits in the chunk. 

0 - Set candidate pinnacle point list (PPc) to be the list of all summits

1 - While PPc isn't empty: (gotta check all candidates):

1.0 - Find highest elevation point in PPc (currentPPc)

1.1 - Find currentPPc's chunk

1.2 - Find all points within currentPPc's viewshed (currentPPc_VS) and remove from PPC (use STRM30?, investigate the fastest way to do this)

1.3 - If no points in currentPPc_VS have a higher elevation than currentPPc: (Check if this is a pinnacle point)

1.3.0 - Add currentPPc to list of found pinnacle points


![Image](https://github.com/jgbreault/PinnaclePoints/blob/main/summits300.png)
![Image](https://github.com/jgbreault/PinnaclePoints/blob/main/RatioOfFoundPinnaclePointsAboveProminence.png)