/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/ControlledIFS/SphTiling3.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin
    
    Mandelbrot Set Plugin v2 - Copyright 2008,2009 Jed Kelsey

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
*/

// Must define this structure before we include apoplugin.h
typedef struct 
{
    
} Variables;
static double X=0.01,Y=0.02;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("SphTiling3");


// Define the Variables
APO_VARIABLES(

);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{

}

void SphericalInternal(double R02,double XIn,double YIn,double *XOut,double *YOut)
{
     double r2=sqr(XIn)+sqr(YIn);//+ 1E-6;
     *XOut=R02/r2*XIn;
     *YOut=R02/r2*YIn;
}
void BlurInternal(double Size,double *Xout,double *Yout)
{
     double r=Size*random01();
     double a=M_2PI*random01(),sina,cosa;
     fsincos(a,&sina,&cosa);
     *Xout=r*cosa;
     *Yout=r*sina;
}    

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
        double X1,Y1,U1,V1,U0,V0;
        double W=random01();
        if (W<0.8333333)
        {
            int N=floor(3*random01());
            double R=1/M_SQRT3_2;
            double X0=R*cos(N*M_2PI/3);
            double Y0=R*sin(N*M_2PI/3);
            SphericalInternal(1.0,X-X0,Y-Y0,&U1,&V1);
            U1+=X0;
            V1+=Y0;
        }
        else
        {
            
            SphericalInternal(1.0,X,Y,&U0,&V0);
            U1=0.0411259*(U0*0.5-V0*M_SQRT3_2);
            V1=0.0411259*(U0*M_SQRT3_2+V0*0.5);
        }
            
        X=U1; Y=V1;
        
        FPx+=U1; FPy+=V1;


    return TRUE;
}
