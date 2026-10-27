/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/bCollide.c
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

typedef struct
{
	double bCollide_a;
	int bCollide_num;
	double bCa;
    double bCn_pi;
    double bCa_bCn;
    double pi_bCn;
} Variables;

// (SDK header apoplugin.h implied)

/* Place plugin name here */
APO_PLUGIN("bCollide");

APO_VARIABLES(
	VAR_REAL_CYCLE(bCollide_a, 0.0, 1.0, 0.0),
	VAR_INTEGER_RANGE(bCollide_num, 1, INT_MAX, 1)
);

/* This function is called once before the calculation starts.
   Prepare everything you need to do only once here.
   You must call the argument "vp"
*/
int PluginVarPrepare(Variation* vp)
{
	VAR(bCn_pi) = (double) VAR(bCollide_num) * M_1_PI;
    VAR(pi_bCn) = M_PI / (double)VAR(bCollide_num) ;
    VAR(bCa) = M_PI * VAR(bCollide_a);
	VAR(bCa_bCn) = VAR(bCa) / (double) VAR(bCollide_num);
    // must return true
    return TRUE; 
}

/* This function is called during calculation.
   You must call the argument "vp"
*/
int PluginVarCalc(Variation* vp)
{
    double tau, sigma;
    double temp;
    double cosht,sinht;
    double sins, coss;
    int alt;
    
    tau = 0.5 * ( log( sqr(FTx + 1.0) + sqr(FTy) ) - log( sqr(FTx - 1.0) + sqr(FTy)) ) ;
	sigma = M_PI - atan2(FTy, FTx + 1.0) - atan2(FTy, 1.0 - FTx);
    	
    alt = (int)( sigma * VAR(bCn_pi));
    if ( alt % 2 == 0)
       	sigma = alt * VAR(pi_bCn) + fmod( sigma + VAR(bCa_bCn), VAR(pi_bCn));
	else
        sigma = alt * VAR(pi_bCn) + fmod( sigma - VAR(bCa_bCn), VAR(pi_bCn));
    
    sinhcosh(tau, &sinht, &cosht);
	fsincos(sigma, &sins, &coss);
    temp = cosht - coss;
    FPx += VVAR * sinht / temp;
    FPy += VVAR * sins / temp;
    
    // must return true
    return TRUE;
}
