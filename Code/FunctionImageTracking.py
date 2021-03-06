
from IPython.html.widgets import interact

from cmath import *
import scipy.io
import math
import numpy as np
import scipy as sp
import scipy.signal as sg
import matplotlib.pyplot as plt

import skimage
import skimage.filters as skif
import skimage.data as skid

from skimage.draw import ellipse
from skimage.draw import ellipse_perimeter
from skimage.morphology import label
from skimage.measure import regionprops
from skimage.transform import rotate
from skimage import img_as_float
from skimage import img_as_int
from skimage import exposure
from skimage.filters import threshold_otsu, threshold_local

import matplotlib.cm as cmx
import matplotlib.colors as colors
import seaborn as sns
import pickle


sns.set(style="ticks")
values = range(100)
RdYlBu = cm = plt.get_cmap('RdYlBu') 
cNorm  = colors.Normalize(vmin=0, vmax=values[-1])
scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=RdYlBu)
Bl = scalarMap.to_rgba(values[-10])
Re = scalarMap.to_rgba(values[10])

#sns.set_style("whitegrid")
#sns.set_style("whitegrid", {"legend.frameon": True})

rc={'font.size': 15, 'axes.labelsize': 15, 'legend.fontsize': 15.0, 
    'axes.titlesize': 15, 'xtick.labelsize':15, 'ytick.labelsize': 15}
plt.rcParams.update(**rc)
sns.set(rc=rc)
plt.rcParams.update({'font.size': 22})



def Binarize(img,Offset):
    bw = threshold_local(img,39, offset=Offset)
    #bw = skimage.morphology.remove_small_objects(1-bw>0,SmallSize)   
    bw1 = skimage.morphology.remove_small_objects((bw-36)>0,50)  
    bw = skimage.morphology.remove_small_objects(1-bw1>0,2000) 
    se=skimage.morphology.disk(5)
    bw=skimage.morphology.binary_closing(bw,se)
    return bw

class Ellipse:
     def __init__(self,cx,cy,L,l,Angle):
         self.cx =cx
         self.cy =cy
         self.L =L
         self.l =l
         self.Angle =Angle
            
def DrawEllipse(ell,N):
    t=np.linspace(0,2*math.pi,20)
    R=np.array([[math.cos(ell.Angle),-math.sin(ell.Angle)],[math.sin(ell.Angle),math.cos(ell.Angle)]])
    a=ell.L*np.cos(t)
    b=ell.l*np.sin(t)
    xy=np.vstack((a,b))
    xy=np.dot(R,xy)
    xy=xy+np.array([[ell.cx],[ell.cy]])
    return xy

def FitEllipse(bw):
    props=skimage.measure.regionprops((bw==1)*1)
    props=props[0]
    Y,X=props.coords[:,0],props.coords[:,1]
    return Ellipse(props.centroid[1],props.centroid[0],props.major_axis_length/2.,props.minor_axis_length/2.,-props.orientation)

def ComputeCurvature(X,Y,Ell1,Ell2):
    cx1=Ell1.cx;cy1=Ell1.cy;Angle1=Ell1.Angle
    cx2=Ell2.cx;cy2=Ell2.cy;Angle2=Ell2.Angle
    
    # Find Intersection between minor axis:
    SmallAxes1=np.transpose(np.array([-math.sin(Angle1),math.cos(Angle1)]))
    SmallAxes2=np.transpose(np.array([-math.sin(Angle2),math.cos(Angle2)]))
    
    A=np.array([[SmallAxes1[0],-SmallAxes2[0]],[SmallAxes1[1],-SmallAxes2[1]]])
    b=np.array([cx2-cx1,cy2-cy1])
    t=np.linalg.solve(A,b)
    
    CenterCurv=np.array([cx1,cy1])+t[0]*SmallAxes1

    Rmoy=np.mean(np.sqrt((X-CenterCurv[0])**2+(Y-CenterCurv[1])**2));
    Center1=np.array([cx1,cy1])
    Center2=np.array([cx2,cy2])
    cc1=np.hstack([Center1-CenterCurv,0])
    cc2=np.hstack([Center2-CenterCurv,0])
    V=np.cross(cc1,cc2)
    Sign=2.*(V[2]>0)-1;
    C=np.array([Sign*1/Rmoy,CenterCurv[0],CenterCurv[1],t[0],t[1]])
    return C

def SplitEllipse(bw,img,Ell0,flag):
    Y,X=np.nonzero(bw)
    #Split according to small axis of 1st order ellipse:
    Dot=(X-Ell0.cx)*math.cos(Ell0.Angle)+(Y-Ell0.cy)*math.sin(Ell0.Angle)
    
    ind1=np.nonzero(Dot>0)
    img1=np.zeros(bw.shape)
    img1[Y[ind1],X[ind1]]=1
    print(len(ind1))
    Ellipse1=FitEllipse(img1)
    
    ind2=np.nonzero(Dot<=0)
    img2=np.zeros(bw.shape)
    img2[Y[ind2],X[ind2]]=1
    Ellipse2=FitEllipse(img2)
    
    I1 = np.ma.masked_where(img1==0, img1)
    I2 = np.ma.masked_where(img2==0, img2)
    
    C=ComputeCurvature(X,Y,Ellipse1,Ellipse2)
    Curvature=C[0]
    
    if flag==1:
        plt.xlim([0,img.shape[1]])
        plt.ylim([0,img.shape[0]])
        plt.imshow(img, cmap=plt.cm.gray);
        plt.gca().invert_yaxis()
        plt.axis('off');
        
        plt.imshow(I1, cmap=plt.cm.winter, alpha=0.4)
        plt.imshow(I2, cmap=plt.cm.summer, alpha=0.4)
    
        xy= DrawEllipse(Ell0,100)
        plt.plot(xy[0,:],xy[1,:],linewidth=2.0,ls='--',c='k')
        xy= DrawEllipse(Ellipse1,100)
        plt.plot(xy[0,:],xy[1,:],linewidth=2.0,ls='--',c='b')
        xy= DrawEllipse(Ellipse2,100)
        plt.plot(xy[0,:],xy[1,:],linewidth=2.0,ls='--',c='g')
        # Display small axis:::
        plt.plot( [Ellipse1.cx,Ellipse1.cx-C[3]*math.sin(Ellipse1.Angle)] , [Ellipse1.cy,Ellipse1.cy+C[3]*math.cos(Ellipse1.Angle)],'-b')
        plt.plot( [Ellipse2.cx,Ellipse2.cx-C[4]*math.sin(Ellipse2.Angle)] , [Ellipse2.cy,Ellipse2.cy+C[4]*math.cos(Ellipse2.Angle)] ,'-g')


        plt.scatter(Ellipse1.cx,Ellipse1.cy,s=10)
        plt.scatter(Ellipse2.cx,Ellipse2.cy,s=10)
        plt.scatter(C[1],C[2],s=100,c=[0,0,0],alpha=1)
    
    return Curvature
