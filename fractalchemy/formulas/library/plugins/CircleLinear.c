/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/Circles/CircleLinear.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

#define AM (1.0 / 2147483647.0)   /* (was missing from the source) */
/*
    Apophysis Plugin

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
    
    I've used some ideas and routines from the beautiful introduction to Perlin noise by Hugo Elias
    http://freespace.virgin.net/hugo.elias/models/m_perlin.htm
*/

// Must define this structure before we include apoplugin.h
typedef struct
{
    double CircleLinear_Sc, CircleLinear_K,CircleLinear_Reverse,CircleLinear_Dens1,CircleLinear_Dens2;
    double CircleLinear_X,CircleLinear_Y;
    int CircleLinear_Seed;
    
    

    
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("CircleLinear");

// Define the Variables
APO_VARIABLES(
    
    VAR_REAL(CircleLinear_Sc,1.0),
    VAR_REAL(CircleLinear_K,0.5),
    VAR_REAL(CircleLinear_Dens1,0.5),
    VAR_REAL(CircleLinear_Dens2,0.5),
    VAR_REAL(CircleLinear_Reverse,1.0),
    VAR_REAL(CircleLinear_X,10.0),
    VAR_REAL(CircleLinear_Y,10.0),
    VAR_INTEGER(CircleLinear_Seed,0)
    
  
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    

    // Always return TRUE.
    return TRUE;
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
        double DiscretNoise2 (int X, int Y) 
        {
            int n = X + Y * 57;
            n = (n<<13) ^ n;
	        return( (n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff)*AM;
        }
        
        
            
            double X, Y, Z,Z1, U, V;
            int M,N;
            
            
                
                
                M=floor(0.5*FTx/VAR(CircleLinear_Sc));
                N=floor(0.5*FTy/VAR(CircleLinear_Sc));
                X=FTx-(M*2+1)*VAR(CircleLinear_Sc);
                Y=FTy-(N*2+1)*VAR(CircleLinear_Sc);
                U=sqrt(X*X+Y*Y);
                V=(0.3+0.7*DiscretNoise2(M+10,N+3))*VAR(CircleLinear_Sc);                
                Z1=DiscretNoise2(M+VAR(CircleLinear_Seed),N);
            if ((Z1<VAR(CircleLinear_Dens1))&&(U<V))
            {
                if (VAR(CircleLinear_Reverse)>0)
                {
                   if (Z1<VAR(CircleLinear_Dens1)*VAR(CircleLinear_Dens2))
                   {
                      X=VAR(CircleLinear_K)*X;
                      Y=VAR(CircleLinear_K)*Y;
                   }
                   else
                   {
                      Z=V/U*(1-VAR(CircleLinear_K))+VAR(CircleLinear_K);
                      X=Z*X;
                      Y=Z*Y;
                   }
                }
                else
                {
                   if (Z1>VAR(CircleLinear_Dens1)*VAR(CircleLinear_Dens2))
                   {
                      X=VAR(CircleLinear_K)*X;
                      Y=VAR(CircleLinear_K)*Y;
                   }
                   else
                   {
                      Z=V/U*(1-VAR(CircleLinear_K))+VAR(CircleLinear_K);
                      X=Z*X;
                      Y=Z*Y;
                   }
                }
            }
            
                                 
            FPx+= VVAR*(X+(M*2+1)*VAR(CircleLinear_Sc));
            FPy+= VVAR*(Y+(N*2+1)*VAR(CircleLinear_Sc));
            

    return TRUE;
}

