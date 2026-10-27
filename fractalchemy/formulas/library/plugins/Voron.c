/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/VoronoiDiagram/voron.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

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
*/

// Must define this structure before we include apoplugin.h
typedef struct
{
    
    double Voron_K,Voron_Step;
    int Voron_XSeed, Voron_YSeed,Voron_Num;
    

    
} Variables;
#define IA 16807
#define IM 2147483647
#define AM (1./IM)
// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("Voron");

// Define the Variables
APO_VARIABLES(
    VAR_REAL(Voron_K, 0.99),
    VAR_REAL(Voron_Step, 0.25),
    VAR_INTEGER_RANGE(Voron_Num,1,25,1),
    VAR_INTEGER(Voron_XSeed,3),
    VAR_INTEGER(Voron_YSeed,7)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    
    
    
    return TRUE;
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    double DiscretNoise (int X)
    {
            int n = X ;
            n = (n<<13) ^ n;
	        return( (n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff)*AM;
    }
    
      int i,j,l,K,M,M1,N,N1;
      double R,Rmin,OffsetX,OffsetY,X0,Y0,X,Y;
      Rmin=20.0;
      M=floor(FTx/VAR(Voron_Step));
      N=floor(FTy/VAR(Voron_Step));
      for (i=-1; i<2; i++)
      {
           M1=M+i;
           for (j=-1; j<2; j++)
           {
               N1=N+j;
               K=1+floor(VAR(Voron_Num)*DiscretNoise (19*M1+257*N1+VAR(Voron_XSeed)));
               for (l=0; l<K; l++)
               {
                   X=(DiscretNoise (l+64*M1+15*N1+VAR(Voron_XSeed))+M1)*VAR(Voron_Step);
                   Y=(DiscretNoise (l+21*M1+33*N1+VAR(Voron_YSeed))+N1)*VAR(Voron_Step);
           
                   OffsetX=FTx-X;
                   OffsetY=FTy-Y;
           
                   R=sqrt(OffsetX*OffsetX+OffsetY*OffsetY);
           
                   if (R<Rmin)
                   {
                      Rmin=R;
                      X0=X;
                      Y0=Y;
                   }
               }
           }
      }
      FPx += VVAR*(VAR(Voron_K)*(FTx-X0)+X0);
      FPy += VVAR*(VAR(Voron_K)*(FTy-Y0)+Y0);
         
    

    return TRUE;
}

