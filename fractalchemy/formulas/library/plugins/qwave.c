/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/qwave_by_Keeps/qwave.c
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
} Variables;
// (SDK header apoplugin.h implied)
// Set the name of this plugin
APO_PLUGIN("qwave");
// Define the Variables
APO_VARIABLES(
);
// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    return TRUE; // Always return TRUE.
}
// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
  double half = ( (FTx + FTy + FTz) * 0.5 ) + EPS;
  double ang1 = atan2((FTy  + EPS), (FTx + EPS));
  double ang2 = atan2( (ang1 + EPS) , half );  
  double Aang = sqr(FTx + ang2) + sqr(FTy + ang2) + sqr(FTz + ang2) - half;
  double Bang = sqr(FTx - ang2) + sqr(FTy - ang2) + sqr(FTz - ang2) + half;
      FPx += VVAR * FTx;
      FPy += VVAR * FTy * cos(Aang) * cos(Bang);
      FPz += VVAR * sin(FTy);
    return TRUE;
}
