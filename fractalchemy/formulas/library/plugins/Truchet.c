/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/Truchet.c
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
        int Truchet_extended;
        double Truchet_exponent;
        double Truchet_arc_width;
        double Truchet_rotation;
        double Truchet_size;
        double Truchet_seed;

} Variables;

// (SDK header apoplugin.h implied)
// (missing include apotest.h)

// Set the name of this plugin
APO_PLUGIN("Truchet");

// Define the Variables
APO_VARIABLES(
VAR_INTEGER_RANGE(Truchet_extended, 0, 1, 0),
VAR_REAL_CYCLE(Truchet_exponent, 0.001, 2.0, 2.0),
VAR_REAL_CYCLE(Truchet_arc_width, 0.001, 1.0, 0.5),
VAR_REAL(Truchet_rotation,  0.0),
VAR_REAL_CYCLE(Truchet_size, 0.001, 10.0, 1.0),
//VAR_INTEGER_RANGE(Truchet_seed, 0, 99999,  12345)
VAR_REAL(Truchet_seed, 50.000)

);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    return TRUE; // Always return TRUE.
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{

//APO VARIABLES
    int extended = VAR(Truchet_extended);
    double n = VAR(Truchet_exponent);
    double tdeg = VAR(Truchet_rotation);
    double width = VAR(Truchet_arc_width);
    double size = VAR(Truchet_size);
    double seed = fabs(VAR(Truchet_seed));
    double seed2 = sqrt(seed + (seed/2) + EPS) / ((seed * 0.5) + EPS) * 0.25;
 

//VARIABLES   
    double x, y;
    int intx = 0;
    int inty = 0;
    double r = -tdeg;
    double r0 = 0.0;
    double r1 = 0.0;
    double rmax = 0.5 * ( pow(2.0, 1.0/n) -1.0) * width;
    double scale = (cos(r) - sin(r)) / VVAR;
    double tiletype=0.0;
    double randint=0.0;
    double modbase=65535.0;
    double multiplier=32747.0;//1103515245;
    double offset=12345.0;
    double niter=0.0;
    int randiter = 0;
 
//INITIALISATION 
   
    x = FTx*scale;
    y = FTy*scale;
    intx = round(x);
    inty = round(y);
    
    r = x - intx;
      if (r < 0.0)
         x = 1.0+r;
      else
         x = r;
    
    r = y - inty;
      if (r < 0.0)
         y = 1.0+r;
      else
         y = r;
          
//CALCULATE THE TILE TYPE
    if (seed == 0.0) tiletype == 0.0;  
    else if (seed == 1.0) tiletype == 1.0;
    else {
         if (extended == 0) {
             double xrand = round(FTx);
             double yrand = round(FTy);
             xrand = xrand * seed2;
             yrand = yrand * seed2;
             niter = xrand + yrand + xrand*yrand;
             randint = (niter + seed) * seed2 / 2.0;
             randint = fmod((randint * multiplier + offset),modbase);
         }
         else {
             seed = floor(seed); 
             int xrand = round(FTx);
             int yrand = round(FTy);
             niter = abs(xrand + yrand + xrand*yrand);
             randint = seed + niter;
             randiter = 0;
             while (randiter < niter) {
                   randiter += 1;
                   randint = fmod((randint * multiplier+offset), modbase);
             }
         }
    tiletype = fmod(randint, 2.0);//randint%2;
    }
  
//DRAWING THE POINTS
    if (extended == 0) { //Fast drawmode
        if (tiletype < 1.0) {   
           r0 = pow((pow(fabs(x), n) + pow(fabs(y), n)), 1.0/n);
           r1 = pow((pow(fabs(x-1.0), n) + pow(fabs(y-1.0), n)), 1.0/n);       
        }
        else {
           r0 = pow((pow(fabs(x-1.0), n) + pow(fabs(y), n)), 1.0/n);
           r1 = pow((pow(fabs(x), n) + pow(fabs(y-1.0), n)), 1.0/n);
        }                 
    }  
    else {
        if (tiletype == 1.0) {  //Slow drawmode 
           r0 = pow((pow(fabs(x), n) + pow(fabs(y), n)), 1.0/n);
           r1 = pow((pow(fabs(x-1.0), n) + pow(fabs(y-1.0), n)), 1.0/n);       
        }
        else {
           r0 = pow((pow(fabs(x-1.0), n) + pow(fabs(y), n)), 1.0/n);
           r1 = pow((pow(fabs(x), n) + pow(fabs(y-1.0), n)), 1.0/n);
        }
    }
  
         
    r = fabs(r0 - 0.5) / rmax;
       if (r < 1.0) {
            FPx += size*(x + floor(FTx));
            FPy += size*(y + floor(FTy));
       }
    
    r = fabs(r1 - 0.5) / rmax;
       if (r < 1.0) {
            FPx += size*(x + floor(FTx));
            FPy += size*(y + floor(FTy));
       }

    return TRUE;
}
