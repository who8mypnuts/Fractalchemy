/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/ControlledIFS/SphTiling4.c
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
APO_PLUGIN("SphTiling4");


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
void BlurInternal1(double Size,double *Xout,double *Yout)
{
     double r=Size*sqrt(sqrt(random01()));
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
        if (W<0.32258064516129)
        {
            int N=floor(4*random01());
            double R=1/M_SQRT1_2;
            double X0=R*cos(N*M_PI_2);
            double Y0=R*sin(N*M_PI_2);
            SphericalInternal(1.0,X-X0,Y-Y0,&U1,&V1);
            U1+=X0;
            V1+=Y0;
        }
        else
        {
            if (W<0.967741935483871)
            {
               X1=0.28252*M_SQRT1_2*(X-Y);
               Y1=0.28252*M_SQRT1_2*(X+Y);
               SphericalInternal(1.0,X1,Y1,&U1,&V1);               
            }
            else
            {
                
                    
                       BlurInternal1(0.820426,&U1,&V1);
                       int N=floor(4*random01());
                       U1+=2.71945*cos(N*M_PI_2);
                       V1+=2.71945*sin(N*M_PI_2);
                   
               
            }
        }
        X=U1; Y=V1;
        FPx+=U1; FPy+=V1;


    return TRUE;
}
