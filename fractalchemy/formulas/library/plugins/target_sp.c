/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        target_sp.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    Copyright (C) 2007-2013 Michael Faber

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
	double tarsp_twist;
	double tarsp_n_of_sp;
	double tarsp_size;
	double tarsp_tightness;
	// -----------------------
	double t_size_2;
	double _rota, _rotb;

} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("target_sp");

// Define the Variables
APO_VARIABLES(
	VAR_REAL_CYCLE(tarsp_twist, 0.0, M_2PI, 0.0),
	VAR_REAL_CYCLE(tarsp_n_of_sp, 0.0, M_2PI, 0.0),
	VAR_REAL_RANGE(tarsp_size, EPS, DBL_MAX, 1.0),
	VAR_REAL(tarsp_tightness, 1.0)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
	VAR(t_size_2) = 0.5 * VAR(tarsp_size);
    VAR(_rota) = M_PI * VAR(tarsp_twist);
    VAR(_rotb) = -M_PI + VAR(_rota);

    return TRUE; // Always return TRUE.
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
	double a = atan2(FTy, FTx);
	double r = sqrt( sqr(FTx) + sqr(FTy));
	double s, c;
	//double t = log(r);
	double t =  VAR(tarsp_tightness) * log(r) + VAR(tarsp_n_of_sp) * M_1_PI * (a + M_PI);

	if ( t < 0.0)
		t -= VAR(t_size_2);

	t = fmod (fabs(t), VAR(tarsp_size));

	if (  t < VAR(t_size_2))
		a += VAR(_rota);
	else
		a += VAR(_rotb);

	fsincos( a, &s, &c);


	FPx += r * c;
	FPy += r * s;


    return TRUE;
}
