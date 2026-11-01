# The bundled fragment library — where it comes from

`Include/` and `Examples/` are the example files distributed with **FragM** (Fragmentarium, 3Dickulus's fork,
https://github.com/3Dickulus/FragM — the `Examples` submodule at https://github.com/3Dickulus/Fragmentarium_Examples_Folder),
copied unchanged. They are the fragments the Fragments window uses as its built-in library and as its compatibility
test corpus.

* Fragmentarium is Copyright (C) 2010-2014 Mikael Hvidtfeldt Christensen, 2015-2020 Richard Paquette (3Dickulus),
  GPL-3 (the includes are "licensed and distributed under the LPGL or GPL license where applicable").
* Fragments marked `user@hex` in their header were submitted by that user; many fragments carry their own
  author and licence in the header — **check the file header before redistributing a fragment**.
* `Examples/Community/gannjondal/` are gannjondal's Newton fragments from https://github.com/gannjondal/fragm-formulas
  (LGPL, see that repository).
* `Include/Ditch-River*.hdr` is the Ditch-River panorama by 'Blotchi' (http://www.hdrlabs.com/sibl/archive.html),
  CC BY-NC-SA 3.0 — see `Include/Ditch-River-License.txt`.
* Textures (`texture.jpg`, `texture2.jpg`, `vigga.jpg`, `seamless-texture.jpg`, `cubemap.png`) are from the same
  distribution.

The example repository's submodules (3DickUlus, kosalos, mclarekin, TGlad, neozhaoliang, gannjondal, Kashaders,
LoicVDB, Claude) are not bundled; their fragments can be added to the library as a folder.

Acknowledgement (from the FragM examples README): much of the inspiration and formulas for Fragmentarium came from
the community at FractalForums, including Tom Beddard, Jan Kadlec, Iñigo Quilez, Buddhi, Jesse, and others; special
thanks to Knighty and Kali.

## Added by Fractalchemy

* `Include/Primitives.frag` — signed distance primitives, operators and fractal folds collected for the Fragments
  window. Sources: Inigo Quilez's distance functions (https://iquilezles.org/articles/distfunctions/, MIT), the
  hg_sdf library by Mercury (http://mercury.sexy/hg_sdf/, MIT), Jon Baker's *Distance Estimator Compendium*
  (https://jbaker.graphics/writings/DEC.html, CC BY-NC-SA 3.0; the author of each borrowed function is named in a
  comment: tholzer, yx, TLC123, FabriceNeyret2, dr2, kamoshika, blackle), and Akleman & Chen's generalized distance
  functions (via hg_sdf). It includes `QuilezLib.frag`.
* `Examples/Primitives/` — fragments written for Fractalchemy on top of `Primitives.frag` (`Chain Maille.frag` is
  athibaul's chain-maille formula from the Compendium, CC BY-NC-SA 3.0).
* `Examples/Distance Estimator Compendium/` — a selection of the Compendium's fractal estimators (gaziya5 / gaz,
  kamoshika, yonatan, Kali, Nameless, Jos Leys & Knighty via tdhooper, Lewpen, butadiene, michael0884, mrange —
  CC BY-NC-SA 3.0 unless the header says otherwise; `iq - Apollonian.frag` is Inigo Quilez's, MIT), each wrapped in
  a `DE-Raytracer.frag` fragment with sliders and a preset. The formulas are the authors'; the parameterisation is ours.
