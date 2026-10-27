/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/Circles/CircleRand.c
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
    double CircleRand_Sc,CircleRand_Dens;
    double CircleRand_X,CircleRand_Y;
    int CircleRand_Seed;
   
    

    
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("CircleRand");

// Define the Variables
APO_VARIABLES(
    
    VAR_REAL(CircleRand_Sc,1.0),
    VAR_REAL(CircleRand_Dens,0.5),
    VAR_REAL(CircleRand_X,10.0),
    VAR_REAL(CircleRand_Y,10.0),
    VAR_INTEGER(CircleRand_Seed,0)
    
  
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
        
        
            
            double X, Y, Z, U, V;
            int M,N;
            
            do
            {
                
                X=VAR(CircleRand_X)*(1-2*random01());
                Y=VAR(CircleRand_Y)*(1-2*random01());
                M=floor(0.5*X/VAR(CircleRand_Sc));
                N=floor(0.5*Y/VAR(CircleRand_Sc));
                X=X-(M*2+1)*VAR(CircleRand_Sc);
                Y=Y-(N*2+1)*VAR(CircleRand_Sc);
                U=sqrt(X*X+Y*Y);
                                
            }
            while ((DiscretNoise2(M+VAR(CircleRand_Seed),N)>VAR(CircleRand_Dens))||(U>(0.3+0.7*DiscretNoise2(M+10,N+3))*VAR(CircleRand_Sc)));
                                 
            FPx+= VVAR*(X+(M*2+1)*VAR(CircleRand_Sc));
            FPy+= VVAR*(Y+(N*2+1)*VAR(CircleRand_Sc));
            

    return TRUE;
}

