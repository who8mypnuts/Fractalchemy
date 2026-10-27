/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/z.c
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
	double z_hypergon;
	int z_hypergon_n;
	double z_hypergon_r;
	double hypergon_d;
	double hypergon_n;

	double z_star;
	int z_star_n;
	double z_star_slope;
	double star_slope;
	double star_n;

	double z_lituus;
	double z_lituus_a;
	double lituus_a;

	double z_super;
	double z_super_m;
	double z_super_n1;
	double z_super_n2;
	double z_super_n3;
	double super_m;
	double super_n1;

} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("z");

// Define the Variables
APO_VARIABLES(
	VAR_REAL(z_hypergon, 0.0),
	VAR_INTEGER_RANGE(z_hypergon_n, 3, INT_MAX, 4),
	VAR_REAL_RANGE(z_hypergon_r, 0.0, DBL_MAX, 1.0),

	VAR_REAL(z_star, 0.0),
	VAR_INTEGER_RANGE(z_star_n, 3, INT_MAX, 5),
	VAR_REAL_RANGE(z_star_slope, EPS, M_PI_2, 2.0),

	VAR_REAL(z_lituus, 0.0),
	VAR_REAL(z_lituus_a, 1.0),

	VAR_REAL(z_super, 0.0),
	VAR_REAL(z_super_m, 1.0),
	VAR_REAL(z_super_n1, 1.0),
	VAR_REAL(z_super_n2, 1.0),
	VAR_REAL(z_super_n3, 1.0)


);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    VAR(hypergon_d) = sqrt( 1.0 + sqr(VAR(z_hypergon_r)));
    VAR(hypergon_n) = (double)VAR(z_hypergon_n);

    VAR(lituus_a) = -VAR(z_lituus_a);

    VAR(star_n) = (double)VAR(z_star_n);
    VAR(star_slope) = tan(VAR(z_star_slope));

    VAR(super_m) = VAR(z_super_m) / 4.0;
    VAR(super_n1) = - 1.0 / (VAR(z_super_n1) + EPS);


    return TRUE; // Always return TRUE.
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
	const double a = atan2(FTy, FTx);
	const double a90 = atan2(FTx, -FTy);
	double r;
	double s, c;
	double total = 0.0;
	double temp1, temp2, temp3, temp4;

	if(VAR(z_hypergon) != 0.0)
	{
        temp1 = fmod( fabs(a), M_2PI / VAR(hypergon_n)) - M_PI /  VAR(hypergon_n);
        temp2 = sqr(tan(temp1)) + 1.0;
        if(temp2 >= sqr(VAR(hypergon_d)))
        {
            total += VAR(z_hypergon);
        }
        else
        {
            temp3 = VAR(hypergon_d);
            total += VAR(z_hypergon) * (  VAR(hypergon_d) - sqrt( sqr( VAR(hypergon_d)) - temp2)) / sqrt(temp2);
        }
    }
    if(VAR(z_star) != 0.0)
    {
        temp1 = tan(fabs(fmod( fabs(a), M_2PI / VAR(star_n)) - M_PI / VAR(star_n)));
        total += VAR(z_star) * sqrt(sqr(VAR(star_slope)) * ( 1.0 + sqr(temp1)) / sqr(temp1 + VAR(star_slope)));
    }
    if(VAR(z_lituus) != 0.0)
    {
        total += VAR(z_lituus) * pow( a/M_PI + 1.0, VAR(lituus_a) );
    }
    if(VAR(z_super) != 0.0)
    {
        fsincos(a * VAR(super_m), &s, &c);
        total += VAR(z_super) * pow(pow(fabs(c), VAR(z_super_n2)) + pow(fabs(s), VAR(z_super_n3)), VAR(super_n1));
    }


	r = VVAR * ( sqrt(sqr(FTx) + sqr(FTy)) + total);

	fsincos( a, &s, &c);

	FPx += r * c;
	FPy += r * s;
    return TRUE;
}
