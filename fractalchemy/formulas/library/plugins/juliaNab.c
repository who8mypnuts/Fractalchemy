/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/juliaNab.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    Copyright (C) 2008-2009 Michael Faber

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
	double juliaNab_a;
	double juliaNab_b;
	double juliaNab_separ;
	double juliaNab_n;
	double absN;
	double cN;
} Variables;

// (SDK header apoplugin.h implied)
APO_PLUGIN("juliaNab");
APO_VARIABLES(
	VAR_REAL(juliaNab_n, 1.0),
	VAR_REAL(juliaNab_a, 1.0),
	VAR_REAL(juliaNab_b, 1.0),
	VAR_REAL(juliaNab_separ, 1.0),
);

int PluginVarPrepare(Variation* vp)
{	double jun = EPS;
	if(abs(VAR(juliaNab_n))>EPS) jun = VAR(juliaNab_n);
    VAR(absN) = abs(VAR(juliaNab_n));
    VAR(cN) = 1 / jun / 2;
    return TRUE; 
}
int PluginVarCalc(Variation* vp)
{
	double sina = 0;
	double cosa = 0;
	double jun = EPS;
	if(abs(VAR(juliaNab_n))>EPS) jun = VAR(juliaNab_n);
	fsincos((atan2(FTy, pow(FTx,VAR(juliaNab_separ))) + 2*M_PI*floor(random01()*VAR(absN))) / jun, &sina, &cosa);
	double r = VVAR * pow(FTx*FTx + FTy*FTy, VAR(cN)*VAR(juliaNab_a));

	FPx = FPx + r *cosa+VAR(juliaNab_b);
	FPy = FPy + r * sina+VAR(juliaNab_b);
	FPz = FTz;
  
    return TRUE;
}
