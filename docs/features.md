
# Features

This document is a large list of every feature that
has been proposed, discussed, implemented, thrown out,
or in any other way been tracked in this repository.

<style type="text/css" rel="stylesheet">
.full, .part, .plan, .not-plan, .broken {
  color: #ffffff;
  padding: 2pt 4pt;
}
.full {     background-color: rgba(0,218,60, 0.5); }
.part {     background-color: rgba(0,203,231, 0.5); }
.plan {     background-color: rgba(244,243,40, 0.5); }
.not-plan { background-color: rgba(253,134,3, 0.5); }
.broken {   background-color: rgba(223,21,26, 0.5); }
</style>

## Feature Legend

<span class='full'>Fully implemented</span>

<span class='part'>Partially implemented</span>

<span class='plan'>Planned</span>

<span class='not-plan'>Not Planned</span>

<span class='broken'>Fundamentally Broken</span>

## The List


<span class='full'>Native, stand-alone executables for win64 and linux64 OSes</span>

<span class='full'>Embed and extract arbitrary 3rd-party programs</span>

<span class='full'>Run arbitrary 3rd-party programs <span class='part'>and re-start them when they exit</span></span>

<span class='full'>Ensure arbitrary 3rd-party programs exit when main process exits</span>

<span class='part'>Support arbitrary USB serial GPS devices (still need to write to DB)</span>

<span class='part'>Support ADS-B rx from USB RTL-SDR devices (still need to parse some ADS-B values and write to DB)</span>

<span class='part'>Support AIS rx from USB RTL-SDR devices (need to run admin process for detecting + reading AIS data)</span>

<span class='plan'>Support translated UI in English, Spanish, French, Arabic</span>

<details class='plan'>
  <summary>support VIDL radios</summary>
  * RMC parsing as own location <br>
  * PTT message protocols w/ feedback loop <br>
  * TELE message protocols w/ feedback loop <br>
  * DTGT packet handling <br>
</details>

<span class='plan'>Add arbitrary user-defined metadata to map points</span>

<span class='plan'>Support a basic icon set</span>

<span class='plan'>Support milstd 2525 icon set for points</span>

<span class='plan'>Support user graphics layers (aks "overlays")</span>

<span class='plan'>Support milstd 2525 icon set for line/area graphics</span>

<span class='plan'>Support displaying all Layers from embedded GeoServer instance (query every 60s + put in layers list as hidden)</span>

<span class='plan'>Execute arbitrary binaries and runtime artifacts in eapp directory</span>












