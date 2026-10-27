/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/GlynnSim/GlynnSim2.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin
    
    The structure of file and "apoplugin.h" are written by Joel Faber
    
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


typedef struct
{
    
    double GlynnSim2_radius,GlynnSim2_thickness;
    double GlynnSim2_Phi1,GlynnSim2_Phi2,GlynnSim2_Phi10,GlynnSim2_Phi20;
    double GlynnSim2_contrast,GlynnSim2_pow;
    double Gamma,Delta;

    
} Variables;

// (SDK header apoplugin.h implied)


APO_PLUGIN("GlynnSim2");


APO_VARIABLES(
    
    VAR_REAL(GlynnSim2_radius,  1.0),
    VAR_REAL_RANGE(GlynnSim2_thickness, 0.0, 1.0 , 0.1),
    VAR_REAL_RANGE(GlynnSim2_contrast, 0.0, 1.0 , 0.5),
    VAR_REAL(GlynnSim2_pow,  1.5),
    VAR_REAL(GlynnSim2_Phi1,  0.0),
    VAR_REAL(GlynnSim2_Phi2,  360.0)
);


int PluginVarPrepare(Variation* vp)
{
    VAR(GlynnSim2_Phi10)=M_PI*VAR(GlynnSim2_Phi1)/180.0;
    VAR(GlynnSim2_Phi20)=M_PI*VAR(GlynnSim2_Phi2)/180.0;
    VAR(Gamma)=VAR(GlynnSim2_thickness)*(2*VAR(GlynnSim2_radius)+VAR(GlynnSim2_thickness))/(VAR(GlynnSim2_radius)+VAR(GlynnSim2_thickness));
    VAR(Delta)=VAR(GlynnSim2_Phi20)-VAR(GlynnSim2_Phi10);
    VAR(GlynnSim2_pow)=fabs(VAR(GlynnSim2_pow));
    return TRUE;
}


int PluginVarCalc(Variation* vp)
{
    void Circle(double* X,double* Y)
    {
       double sinPhi,cosPhi;
       double r=VAR(GlynnSim2_radius)+VAR(GlynnSim2_thickness)-VAR(Gamma)*random01();
       double Phi=VAR(GlynnSim2_Phi10)+VAR(Delta)*random01();
       fsincos(Phi,&sinPhi,&cosPhi);
       *X=r*cosPhi;
       *Y=r*sinPhi;
    }
    double  r=sqrt(FTx*FTx+FTy*FTy);
    double X,Y,sinY,cosY,Alpha;
    Alpha = VAR(GlynnSim2_radius)/ r;
    
    
    if (r<VAR(GlynnSim2_radius))
    {
       Circle(&X,&Y);
       FPx+=VVAR*X;
       FPy+=VVAR*Y;
       
    }
    else
    {
        if (random01()>VAR(GlynnSim2_contrast)*pow(Alpha,VAR(GlynnSim2_pow)))
        {
                                            
            FPx+=VVAR*FTx;
            FPy+=VVAR*FTy;
        }
        else
        {
            FPx+=VVAR*Alpha*Alpha*FTx;
            FPy+=VVAR*Alpha*Alpha*FTy;
        }
    }
        

    return TRUE;
}

