/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        truc_eralex1.c
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
    int truc_eralex1_Seed,truc_eralex1_Seed1,truc_eralex1_Seed2;
    double truc_eralex1_Step,truc_eralex1_Width;
    double truc_eralex1_K01A,truc_eralex1_K02A,truc_eralex1_K11A,truc_eralex1_K12A,truc_eralex1_K21A,truc_eralex1_K22A,truc_eralex1_K31A,truc_eralex1_K32A;
    double truc_eralex1_K01B,truc_eralex1_K02B,truc_eralex1_K11B,truc_eralex1_K12B,truc_eralex1_K21B,truc_eralex1_K22B,truc_eralex1_K31B,truc_eralex1_K32B;
    //double Truchet_ShiftX, Truchet_ShiftY,Truchet_ShiftC;
    //double Truchet_C,Truchet_D, Truchet_C1,Truchet_D1,Truchet_R;
} Variables;
static double X=0.0,Y=0.0,Z1=0.0,Z2=0.0;

// (SDK header apoplugin.h implied)



// Set the name of this plugin
APO_PLUGIN("truc_eralex1");


// Define the Variables
APO_VARIABLES(
    VAR_INTEGER(truc_eralex1_Seed, 0),
    VAR_REAL(truc_eralex1_K01A,0.5),
    VAR_REAL(truc_eralex1_K02A,0.5),
    VAR_REAL(truc_eralex1_K01B,0.5),
    VAR_REAL(truc_eralex1_K02B,0.5),

    VAR_REAL(truc_eralex1_K11A,0.5),
    VAR_REAL(truc_eralex1_K12A,0.5),
    VAR_REAL(truc_eralex1_K11B,0.5),
    VAR_REAL(truc_eralex1_K12B,0.5),

    VAR_REAL(truc_eralex1_K21A,0.5),
    VAR_REAL(truc_eralex1_K22A,0.5),
    VAR_REAL(truc_eralex1_K21B,0.5),
    VAR_REAL(truc_eralex1_K22B,0.5),

    VAR_REAL(truc_eralex1_K31A,0.5),
    VAR_REAL(truc_eralex1_K32A,0.5),
    VAR_REAL(truc_eralex1_K31B,0.5),
    VAR_REAL(truc_eralex1_K32B,0.5),

    VAR_REAL(truc_eralex1_Step,0.5),
    VAR_REAL(truc_eralex1_Width,0.25)
);

double DN1 (int X)
    {
            int n = X ;
            n = (n<<13) ^ n;
	        return( (n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff)*AM;
    }
// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    /*VAR(K01A)=DN1(VAR(truc_eralex1_Seed1)+77); VAR(K01B)=DN1(VAR(truc_eralex1_Seed2)+77);
    VAR(K02A)=DN1(VAR(truc_eralex1_Seed1)+3); VAR(K02B)=DN1(VAR(truc_eralex1_Seed2)+3);
    VAR(K11A)=DN1(VAR(truc_eralex1_Seed1)+93); VAR(K11B)=DN1(VAR(truc_eralex1_Seed2)+77);
    VAR(K12A)=DN1(VAR(truc_eralex1_Seed1)+2);VAR(K12B)=DN1(VAR(truc_eralex1_Seed2)+2);
    VAR(K21A)=DN1(VAR(truc_eralex1_Seed1)+82);VAR(K21B)=DN1(VAR(truc_eralex1_Seed2)+82);
    VAR(K22A)=DN1(VAR(truc_eralex1_Seed1)+12);VAR(K22B)=DN1(VAR(truc_eralex1_Seed2)+12);
    VAR(K31A)=DN1(VAR(truc_eralex1_Seed1)+26);VAR(K31B)=DN1(VAR(truc_eralex1_Seed2)+26);
    VAR(K32A)=DN1(VAR(truc_eralex1_Seed1)+27);VAR(K32B)=DN1(VAR(truc_eralex1_Seed2)+27);*/
    return TRUE;
}

// Utility function for returning a positive remainder. This function was introduced by
double fmod2(double num, double den)
{
   double tmp = fmod(num,den);
   if ((tmp<0) && (den>0))
     tmp += den;
   return tmp;
}
void LinearInternal(double X0,double Y0,double XIn,double YIn,double *XOut,double *YOut)
{
     *XOut=XIn*0.5+X0;
     *YOut=YIn*0.5+Y0;
}


// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
        double U1=0.0,V1=0.0;
        double Z,K,W,W1;
        int I=floor(4*random01());
        switch (I)
        {
          case 0:
                  LinearInternal(1.0,1.0,X,Y,&U1,&V1);
                  Z1=fmod2(VAR(truc_eralex1_K01A)*Z1+VAR(truc_eralex1_K02A),1.0);
                  Z2=fmod2(VAR(truc_eralex1_K01B)*Z2+VAR(truc_eralex1_K02B),1.0);
                  break ;
          case 1:
                  LinearInternal(-1.0,1.0,X,Y,&U1,&V1);
                  Z1=fmod2(VAR(truc_eralex1_K11A)*Z1+VAR(truc_eralex1_K12A),1.0);
                  Z2=fmod2(VAR(truc_eralex1_K11B)*Z2+VAR(truc_eralex1_K12B),1.0);
                  break ;
          case 2:
                  LinearInternal(1.0,-1.0,X,Y,&U1,&V1);
                  Z1=fmod2(VAR(truc_eralex1_K21A)*Z1+VAR(truc_eralex1_K22A),1.0);
                  Z2=fmod2(VAR(truc_eralex1_K21B)*Z2+VAR(truc_eralex1_K22B),0.5);
                  break ;
          case 3:
                  LinearInternal(-1.0,-1.0,X,Y,&U1,&V1);
                  Z1=fmod2(VAR(truc_eralex1_K31A)*Z1+VAR(truc_eralex1_K32A),1.0);
                  Z2=fmod2(VAR(truc_eralex1_K31B)*Z2+VAR(truc_eralex1_K32B),1.0);
                  break ;
        }

        int M=floor(U1/VAR(truc_eralex1_Step));
        int N=floor(V1/VAR(truc_eralex1_Step));
        double U=U1/VAR(truc_eralex1_Step)-M;
        double V=V1/VAR(truc_eralex1_Step)-N;
        if (DN1(M+34*N+VAR(truc_eralex1_Seed))>0.5)
        {
           if (((V<U+1-VAR(truc_eralex1_Width))&&(V>U+VAR(truc_eralex1_Width)))
               ||((V<U-VAR(truc_eralex1_Width))&&(V>U-1+VAR(truc_eralex1_Width)))) Z=Z1; else Z=Z2;
        }
        else
        {
           if (((V<-U+1-VAR(truc_eralex1_Width))&&(V>-U+VAR(truc_eralex1_Width)))
               ||((V>-U+1+VAR(truc_eralex1_Width))&&(V<-U+2-VAR(truc_eralex1_Width)))) Z=Z1; else Z=Z2;
        }
        X=U1;Y=V1;
        FPx+=U1; FPy+=V1;


        // *(vp->pFPc) = Z;
        *(vp->pColor) = Z;
        Z1=Z;Z2=Z;

        /*
        if (vp->pc_update)
        *(vp->pc_update) |= 0x1; // "normal" (indexed) coloring
        */


    return TRUE;
}
