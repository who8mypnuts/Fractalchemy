/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/ControlledIFS/JuliaRandomN.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

#define AM (1.0 / 2147483647.0)   /* (was missing from the source) */
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
    int JRN_Seed,JRN_N;
    double JRN_dist,JRN_size,JRN_compr,JRN_weight,JRN_X0,JRN_Y0,JRN_Xbl0,JRN_Ybl0;
    
} Variables;
static double X=0.0,Y=0.0;
static int N=0;
// (SDK header apoplugin.h implied)



// Set the name of this plugin
APO_PLUGIN("JuliaRandomN");


// Define the Variables
APO_VARIABLES(
    VAR_INTEGER(JRN_N,3),
    VAR_INTEGER(JRN_Seed,0),
    VAR_REAL(JRN_dist, -0.5),
    VAR_REAL(JRN_size, 1.0),
    VAR_REAL(JRN_compr, 0.27),
    VAR_REAL(JRN_weight, 0.5),
    VAR_REAL(JRN_X0, 0.11),
    VAR_REAL(JRN_Y0, 0.19052559),
    VAR_REAL(JRN_Xbl0, 0.0),
    VAR_REAL(JRN_Ybl0, 0.0)

);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{


}

// Utility function for returning a positive remainder
double fmod2(double num, double den)
{
   double tmp = fmod(num,den);
   if ((tmp<0) && (den>0))
     tmp += den;
   return tmp;
}
double DN1 (int X)
    {
            int n = X ;
            n = (n<<13) ^ n;
	        return( (n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff)*AM;
    }





// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
void JuliaRandomN(double Xin, double Yin, int Niter,double *Xout,double *Yout)
{
     int rN=floor(VAR(JRN_N)*DN1(17*Niter+VAR(JRN_Seed)))+2;
     //int rN=fmod(Niter,VAR(JRN_N))+2;
     double cN=VAR(JRN_dist);
     double T=M_2PI*floor(rN*random01());
     double sina = sin((atan2(Yin, Xin) + T) / rN);
     double cosa = cos((atan2(Yin, Xin) + T) / rN);
     double R=pow(sqr(Xin)+sqr(Yin),cN);
     
     *Xout=R*cosa;
     *Yout=R*sina;
}
void BlurInternal(double Size,double *Xout,double *Yout)
{
     double r=Size*random01();
     double a=M_2PI*random01(),sina,cosa;
     fsincos(a,&sina,&cosa);
     *Xout=r*cosa;
     *Yout=r*sina;
}

        double U,V;
        if (random01()<VAR(JRN_weight))
        {
             BlurInternal(VAR(JRN_size),&U,&V);
             U=U+VAR(JRN_Xbl0);
             V=V+VAR(JRN_Ybl0);
             N=0;
        }
        else
        {
            X=VAR(JRN_compr)*(X+VAR(JRN_X0));
            Y=VAR(JRN_compr)*(Y+VAR(JRN_Y0));
            N+=1;
            JuliaRandomN(X,Y,N,&U,&V);
        }
           
        X=U; Y=V;
        FPx+=U; FPy+=V;
        
        
        //*(vp->pFPc) = Z;
        //FPx+=VVAR*FTx;
        //FPy+=VVAR*FTy;
        



    //if (vp->pc_update)
    //*(vp->pc_update) |= 0x1; // "normal" (indexed) coloring



    return TRUE;
}
