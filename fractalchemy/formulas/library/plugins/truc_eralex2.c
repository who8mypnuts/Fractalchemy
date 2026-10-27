/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        truc_eralex2.c
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
    int truc_eralex2_Seed,truc_eralex2_Seed1,truc_eralex2_Seed2, truc_eralex2_layout, truc_eralex2_style;
    double truc_eralex2_Step,truc_eralex2_Width;
    double truc_eralex2_angle, sinang, cosang;
    double truc_eralex2_K01A,truc_eralex2_K02A,truc_eralex2_K11A,truc_eralex2_K12A,truc_eralex2_K21A,truc_eralex2_K22A,truc_eralex2_K31A,truc_eralex2_K32A;
    double truc_eralex2_K01B,truc_eralex2_K02B,truc_eralex2_K11B,truc_eralex2_K12B,truc_eralex2_K21B,truc_eralex2_K22B,truc_eralex2_K31B,truc_eralex2_K32B;
    //double Truchet_ShiftX, Truchet_ShiftY,Truchet_ShiftC;
    //double Truchet_C,Truchet_D, Truchet_C1,Truchet_D1,Truchet_R;
} Variables;
static double X=0.0,Y=0.0,Z1=0.0,Z2=0.0;
const double M_SQ3_2 = 0.86602540378443864676372317075294;

// (SDK header apoplugin.h implied)



// Set the name of this plugin
APO_PLUGIN("truc_eralex2");


// Define the Variables
APO_VARIABLES(
    VAR_INTEGER(truc_eralex2_Seed, 0),
    VAR_INTEGER_RANGE(truc_eralex2_layout, 0,4,0), // added Dark
    VAR_INTEGER_RANGE(truc_eralex2_style,  0,5,0), // added Dark

    VAR_REAL(truc_eralex2_angle,0.0), // added Dark
    VAR_REAL(truc_eralex2_K01A,0.5),
    VAR_REAL(truc_eralex2_K02A,0.5),
    VAR_REAL(truc_eralex2_K01B,0.5),
    VAR_REAL(truc_eralex2_K02B,0.5),

    VAR_REAL(truc_eralex2_K11A,0.5),
    VAR_REAL(truc_eralex2_K12A,0.5),
    VAR_REAL(truc_eralex2_K11B,0.5),
    VAR_REAL(truc_eralex2_K12B,0.5),

    VAR_REAL(truc_eralex2_K21A,0.5),
    VAR_REAL(truc_eralex2_K22A,0.5),
    VAR_REAL(truc_eralex2_K21B,0.5),
    VAR_REAL(truc_eralex2_K22B,0.5),

    VAR_REAL(truc_eralex2_K31A,0.5),
    VAR_REAL(truc_eralex2_K32A,0.5),
    VAR_REAL(truc_eralex2_K31B,0.5),
    VAR_REAL(truc_eralex2_K32B,0.5),

    VAR_REAL(truc_eralex2_Step,0.5),
    VAR_REAL(truc_eralex2_Width,0.25)
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
    fsincos(VAR(truc_eralex2_angle) * M_PI ,&(VAR(sinang)), &(VAR(cosang)));
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

        switch (VAR(truc_eralex2_layout))
        {
        case 0:
        default:
            // KEPT UNTOUCHED - By Eralex
            switch (I)
            {
              case 0:
                      LinearInternal(1.0,1.0,X,Y,&U1,&V1);
                      Z1=fmod2(VAR(truc_eralex2_K01A)*Z1+VAR(truc_eralex2_K02A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K01B)*Z2+VAR(truc_eralex2_K02B),1.0);
                      break ;
              case 1:
                      LinearInternal(-1.0,1.0,X,Y,&U1,&V1);
                      Z1=fmod2(VAR(truc_eralex2_K11A)*Z1+VAR(truc_eralex2_K12A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K11B)*Z2+VAR(truc_eralex2_K12B),1.0);
                      break ;
              case 2:
                      LinearInternal(1.0,-1.0,X,Y,&U1,&V1);
                      Z1=fmod2(VAR(truc_eralex2_K21A)*Z1+VAR(truc_eralex2_K22A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K21B)*Z2+VAR(truc_eralex2_K22B),0.5);
                      break ;
              case 3:
                      LinearInternal(-1.0,-1.0,X,Y,&U1,&V1);
                      Z1=fmod2(VAR(truc_eralex2_K31A)*Z1+VAR(truc_eralex2_K32A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K31B)*Z2+VAR(truc_eralex2_K32B),1.0);
                      break ;
            }
            break;
        case 1:
            // Symm Square - By Dark
            switch (I)
            {
              case 0:
                      U1 = -0.5* X + 1.0; V1 = 0.5* Y + 1.0;
                      Z1=fmod2(VAR(truc_eralex2_K01A)*Z1+VAR(truc_eralex2_K02A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K01B)*Z2+VAR(truc_eralex2_K02B),1.0);
                      break ;
              case 1:
                      U1 = 0.5* X - 1.0; V1 = 0.5* Y + 1.0;
                      Z1=fmod2(VAR(truc_eralex2_K11A)*Z1+VAR(truc_eralex2_K12A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K11B)*Z2+VAR(truc_eralex2_K12B),1.0);
                      break ;
              case 2:
                      U1 = -0.5* X + 1.0; V1 = -0.5* Y - 1.0;
                      Z1=fmod2(VAR(truc_eralex2_K21A)*Z1+VAR(truc_eralex2_K22A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K21B)*Z2+VAR(truc_eralex2_K22B),0.5);
                      break ;
              case 3:
                      U1 = 0.5* X - 1.0; V1 = -0.5* Y - 1.0;
                      Z1=fmod2(VAR(truc_eralex2_K31A)*Z1+VAR(truc_eralex2_K32A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K31B)*Z2+VAR(truc_eralex2_K32B),1.0);
                      break ;
            }
            break;
        case 2:
            // Sierpinski 45�
            switch (I)
            {
              case 0:
                      U1 = 0.5* X + 1.0; V1 = 0.5* Y + 1.0;
                      Z1=fmod2(VAR(truc_eralex2_K01A)*Z1+VAR(truc_eralex2_K02A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K01B)*Z2+VAR(truc_eralex2_K02B),1.0);
                      break ;
              case 1:
                      U1 = 0.5* X - 1.0; V1 = 0.5* Y - 1.0;
                      Z1=fmod2(VAR(truc_eralex2_K11A)*Z1+VAR(truc_eralex2_K12A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K11B)*Z2+VAR(truc_eralex2_K12B),1.0);
                      break ;
              case 2:
                      U1 = 0.5* X - 1.0; V1 = 0.5* Y + 1.0;
                      Z1=fmod2(VAR(truc_eralex2_K21A)*Z1+VAR(truc_eralex2_K22A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K21B)*Z2+VAR(truc_eralex2_K22B),0.5);
                      break ;
              case 3:
                      U1 = -0.5* X - 1.0; V1 = -0.5* Y + 1.0;
                      Z1=fmod2(VAR(truc_eralex2_K31A)*Z1+VAR(truc_eralex2_K32A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K31B)*Z2+VAR(truc_eralex2_K32B),1.0);
                      break ;
            }
            break;
        case 3:
            // Chair
            switch (I)
            {
              case 0:
                      U1 = 0.5* X; V1 = 0.5* Y;
                      Z1=fmod2(VAR(truc_eralex2_K01A)*Z1+VAR(truc_eralex2_K02A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K01B)*Z2+VAR(truc_eralex2_K02B),1.0);
                      break ;
              case 1:
                      U1 = 0.5* X - 1.0; V1 = 0.5* Y + 1.0;
                      Z1=fmod2(VAR(truc_eralex2_K11A)*Z1+VAR(truc_eralex2_K12A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K11B)*Z2+VAR(truc_eralex2_K12B),1.0);
                      break ;
              case 2:
                      U1 = -0.5* Y - 1.0; V1 = 0.5* X - 1.0;
                      Z1=fmod2(VAR(truc_eralex2_K21A)*Z1+VAR(truc_eralex2_K22A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K21B)*Z2+VAR(truc_eralex2_K22B),0.5);
                      break ;
              case 3:
                      U1 = 0.5* Y + 1.0; V1 = -0.5* X + 1.0;
                      Z1=fmod2(VAR(truc_eralex2_K31A)*Z1+VAR(truc_eralex2_K32A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K31B)*Z2+VAR(truc_eralex2_K32B),1.0);
                      break ;
            }
            break;
        case 4:
            // EquilaterTri
            switch (I)
            {
              case 0:
                      U1 = 0.5* X + 1.0; V1 = 0.5* Y + M_SQ3_2;
                      Z1=fmod2(VAR(truc_eralex2_K01A)*Z1+VAR(truc_eralex2_K02A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K01B)*Z2+VAR(truc_eralex2_K02B),1.0);
                      break ;
              case 1:
                      U1 = 0.5* X - 1.0; V1 = 0.5* Y + M_SQ3_2;
                      Z1=fmod2(VAR(truc_eralex2_K11A)*Z1+VAR(truc_eralex2_K12A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K11B)*Z2+VAR(truc_eralex2_K12B),1.0);
                      break ;
              case 2:
                      U1 = 0.5* X ; V1 = 0.5* Y - M_SQ3_2;
                      Z1=fmod2(VAR(truc_eralex2_K21A)*Z1+VAR(truc_eralex2_K22A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K21B)*Z2+VAR(truc_eralex2_K22B),0.5);
                      break ;
              case 3:
                      U1 = 0.5* X ; V1 = -0.5* Y + M_SQ3_2;
                      Z1=fmod2(VAR(truc_eralex2_K31A)*Z1+VAR(truc_eralex2_K32A),1.0);
                      Z2=fmod2(VAR(truc_eralex2_K31B)*Z2+VAR(truc_eralex2_K32B),1.0);
                      break ;
            }
            break;
        }
        double uu1 = VAR(cosang)*U1 - VAR(sinang)*V1; // rotate truchet
        double vv1 = VAR(sinang)*U1 + VAR(cosang)*V1;

        int M=floor(uu1/VAR(truc_eralex2_Step));
        int N=floor(vv1/VAR(truc_eralex2_Step));
        double U=uu1/VAR(truc_eralex2_Step)-M;
        double V=vv1/VAR(truc_eralex2_Step)-N;

        double chance = DN1(M+34*N+VAR(truc_eralex2_Seed));
        double cir = 0.0;  double square = 0.; int inv = FALSE;

        switch (VAR(truc_eralex2_style)) {
            case 0: // Apo (default) by Eralex
            if (chance>0.5)
            {
               if (((V<U+1-VAR(truc_eralex2_Width))&&(V>U+VAR(truc_eralex2_Width)))
                   ||((V<U-VAR(truc_eralex2_Width))&&(V>U-1+VAR(truc_eralex2_Width)))) Z=Z1; else Z=Z2;
            }
            else
            {
               if (((V<-U+1-VAR(truc_eralex2_Width))&&(V>-U+VAR(truc_eralex2_Width)))
                   ||((V>-U+1+VAR(truc_eralex2_Width))&&(V<-U+2-VAR(truc_eralex2_Width)))) Z=Z1; else Z=Z2;
            }
        break;
        case 1: // Original by Truchet (added width for effect) was with four tiles
         square = MAX(fabs(U-.5),fabs(V-.5)) - 0.5*(1.-VAR(truc_eralex2_Width));
        if (chance < 0.25) {
           if (((square<0) ^ (U > V )) ) Z=Z1;
           else Z=Z2;
        } else if (chance < 0.5) {
           if (((square<0) ^ (U > 1.-V )) ) Z=Z1;
           else Z=Z2;
        } else if (chance < 0.75) {
           if (((square<0) ^ (U < V )) ) Z=Z1;
           else Z=Z2;
        } else {
           if (((square<0) ^ (U < 1.-V )) ) Z=Z1;
           else Z=Z2;
        }

        break;
        case 2: // circle Apo truchet (simulated) :P
        if (chance < 0.5) {
            cir = sqrt((U-1.)*(U-1.)+(V-1.)*(V-1.));
            cir = MIN(cir,sqrt(U*U+V*V));
            cir = fabs(fabs(cir - 0.5)-0.5) - 0.5*(1.-VAR(truc_eralex2_Width));
           if (cir<0) Z=Z1;
           else Z=Z2;
        } else {
            cir = sqrt((U-1.)*(U-1.)+V*V) ;
            cir = MIN(cir,sqrt(U*U+(V-1.)*(V-1.)));
            cir = fabs(fabs(cir - 0.5)-0.5) - 0.5*(1.-VAR(truc_eralex2_Width));
           if (cir<0) Z=Z1;
           else Z=Z2;
        }
        break;
        case 3: // circle Apo truchet plus + tile - looks cool 8)
        if (chance < 0.333333) {
            cir = sqrt((U-1.)*(U-1.)+(V-1.)*(V-1.));
            cir = MIN(cir,sqrt(U*U+V*V));
             cir = fabs(fabs(cir - 0.5)-0.5) - 0.5*(1.-VAR(truc_eralex2_Width));
           if (cir<0) Z=Z1;
           else Z=Z2;
        } else if (chance < 0.666666) {
            cir = sqrt((U-1.)*(U-1.)+V*V) ;
            cir = MIN(cir,sqrt(U*U+(V-1.)*(V-1.)));
             cir = fabs(fabs(cir - 0.5)-0.5) - 0.5*(1.-VAR(truc_eralex2_Width));
           if (cir<0) Z=Z1;
           else Z=Z2;
       } else {
           cir = 0.5*(VAR(truc_eralex2_Width))-MIN(fabs(U-.5),fabs(V-.5)) ; // PLUS!
           if (cir<0) Z=Z1;
           else Z=Z2;
        }
        break;
        case 4: // Original Modded (added width for effect) 8 tiles
         square = MAX(fabs(U-.5),fabs(V-.5)) - 0.5*(1.-VAR(truc_eralex2_Width));
        if (chance < 0.125) {
           if (((square<0) ^ (U > V )) ) Z=Z1;
           else Z=Z2;
        } else if (chance < 0.25) {
           if (((square<0) ^ (U > 1.-V )) ) Z=Z1;
           else Z=Z2;
        } else if (chance < 0.375) {
           if (((square<0) ^ (U < V )) ) Z=Z1;
           else Z=Z2;
        } else if (chance < 0.5) {
           if (((square<0) ^ (U < 1.-V )) ) Z=Z1;
           else Z=Z2;
           // ---------------------
        } else if (chance < 0.625) {
           if (((square<0) ^ (U < 0.5 )) ) Z=Z1;
           else Z=Z2;
        } else if (chance < 0.75) {
           if (((square<0) ^ (V < 0.5 )) ) Z=Z1;
           else Z=Z2;
        } else if (chance < 0.875) {
           if (((square<0) ^ (U > 0.5 )) ) Z=Z1;
           else Z=Z2;
        } else {
           if (((square<0) ^ (V > 0.5 )) ) Z=Z1;
           else Z=Z2;
        }
        break;
        case 5: // circle filled truchet + width for effect
        inv = (M % 2 == 0) ^ (N % 2 == 0);
        if (chance < 0.5) {
            cir = sqrt((U-1.)*(U-1.)+(V-1.)*(V-1.));
            cir = MIN(cir,sqrt(U*U+V*V));
            square = cir;
            cir = fabs(cir) - 0.5;
            // dots effect (suggested a width = 0.25)
            square = MIN(square,sqrt((U-1.)*(U-1.)+V*V));
            square = MIN(square,sqrt(U*U+(V-1.)*(V-1.)));
            square = fabs(square) - VAR(truc_eralex2_Width);
           if ((cir<0) ^ (square<0) ^ inv) Z=Z1;
           else Z=Z2;
        } else {
            cir = sqrt((U-1.)*(U-1.)+V*V) ;
            cir = MIN(cir,sqrt(U*U+(V-1.)*(V-1.)));
            square = cir;
            cir = fabs(cir)- 0.5;
            // dots effect (suggested a width = 0.25)
            square = MIN(square,sqrt((U-1.)*(U-1.)+(V-1.)*(V-1.)));
            square = MIN(square,sqrt(U*U+V*V));
            square = fabs(square) - VAR(truc_eralex2_Width);
           if ((cir<0) ^ (square<0) ^ inv) Z=Z2;
           else Z=Z1;
        }
        break;
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
