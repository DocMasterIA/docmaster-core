/**
 * Listas oficiais por UF (nomes de município) — fonte: repositório `cidades/*.jsx`.
 */
import { AC_CITIES } from '@repo/cidades/acCities.jsx';
import { AL_CITIES } from '@repo/cidades/alCities.jsx';
import { AM_CITIES } from '@repo/cidades/amCities.jsx';
import { AP_CITIES } from '@repo/cidades/apCities.jsx';
import { BA_CITIES } from '@repo/cidades/baCities.jsx';
import { CE_CITIES } from '@repo/cidades/ceCities.jsx';
import { DF_CITIES } from '@repo/cidades/dfCities.jsx';
import { ES_CITIES } from '@repo/cidades/esCities.jsx';
import { GO_CITIES } from '@repo/cidades/goCities.jsx';
import { MA_CITIES } from '@repo/cidades/maCities.jsx';
import { MG_CITIES } from '@repo/cidades/mgCities.jsx';
import { MS_CITIES } from '@repo/cidades/msCities.jsx';
import { MT_CITIES } from '@repo/cidades/mtCities.jsx';
import { PA_CITIES } from '@repo/cidades/paCities.jsx';
import { PB_CITIES } from '@repo/cidades/pbCities.jsx';
import { PE_CITIES } from '@repo/cidades/peCities.jsx';
import { PI_CITIES } from '@repo/cidades/piCities.jsx';
import { PARANA_CITIES } from '@repo/cidades/paranaCities.jsx';
import { RJ_CITIES } from '@repo/cidades/rjCities.jsx';
import { RN_CITIES } from '@repo/cidades/rnCities.jsx';
import { RO_CITIES } from '@repo/cidades/roCities.jsx';
import { RR_CITIES } from '@repo/cidades/rrCities.jsx';
import { RS_CITIES } from '@repo/cidades/rsCities.jsx';
import { SC_CITIES } from '@repo/cidades/scCities.jsx';
import { SE_CITIES } from '@repo/cidades/seCities.jsx';
import { SP_CITIES } from '@repo/cidades/spCities.jsx';
import { TO_CITIES } from '@repo/cidades/toCities.jsx';

/** @type {Record<string, string[]>} */
export const MUNICIPIOS_POR_UF = {
  AC: AC_CITIES,
  AL: AL_CITIES,
  AM: AM_CITIES,
  AP: AP_CITIES,
  BA: BA_CITIES,
  CE: CE_CITIES,
  DF: DF_CITIES,
  ES: ES_CITIES,
  GO: GO_CITIES,
  MA: MA_CITIES,
  MG: MG_CITIES,
  MS: MS_CITIES,
  MT: MT_CITIES,
  PA: PA_CITIES,
  PB: PB_CITIES,
  PE: PE_CITIES,
  PI: PI_CITIES,
  PR: PARANA_CITIES,
  RJ: RJ_CITIES,
  RN: RN_CITIES,
  RO: RO_CITIES,
  RR: RR_CITIES,
  RS: RS_CITIES,
  SC: SC_CITIES,
  SE: SE_CITIES,
  SP: SP_CITIES,
  TO: TO_CITIES,
};
