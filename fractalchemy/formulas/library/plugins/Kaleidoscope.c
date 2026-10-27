/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/kaleidoscopecode.c
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
  double Kaleidoscope_pull;
  double Kaleidoscope_rotate;
  double Kaleidoscope_line_up;
  double Kaleidoscope_x;
  double Kaleidoscope_y;

  

  
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("Kaleidoscope");

// Define the Variables
APO_VARIABLES(
  VAR_REAL(Kaleidoscope_pull,0.0),
  VAR_REAL(Kaleidoscope_rotate,1.0),
  VAR_REAL(Kaleidoscope_line_up,1.0),
  VAR_REAL(Kaleidoscope_x,0.0),
  VAR_REAL(Kaleidoscope_y,0.0),
  

);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
   
    
    return TRUE; // Always return TRUE.
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    double q,w,e,r,t,i;
    
    q = VAR(Kaleidoscope_pull); // pulls apart the 2 sections of the plugin
    w = VAR(Kaleidoscope_rotate); // rotates both halves of the plugin
    e = VAR(Kaleidoscope_line_up) ; 
    r = VAR(Kaleidoscope_x); // changes x co-ordinates
    t = VAR(Kaleidoscope_y); // changes y co-ordinates for 1 part of the plugin

    
 
        
FPx += ((w * FTx) *cos(45)- FTy *sin(45) +  e ) + r   ;

// the if function splits the plugin in two.
if(FTy > 0){ 
FPy += ((w * FTy) * cos(45) + FTx *sin(45)  + q + e ) +t  ;
}
     else{
          (FPy += (w * FTy) * cos(45) + FTx *sin(45)  - q  - e )  ;
          }
 

    
            return TRUE;
}
