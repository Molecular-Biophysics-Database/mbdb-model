|     Unit       |         Unit type       | Convertible to | value conversion expression |
|    :-----:     |       :------------:    |  :----------:  |   :--------------------:    |
|'M'             |         concentration   |      'M'       |        *1                   |
|'mM'            |         concentration   |      'M'       |         *1e-3               |
|'µM'            |         concentration   |      'M'       |         *1e-6               |
|'nM'            |         concentration   |      'M'       |         *1e-9               |
|'pM'            |         concentration   |      'M'       |         *1e-12              |
|'fM'            |         concentration   |      'M'       |         *1e-15              |
|'aM'            |         concentration   |      'M'       |         *1e-18              |
|'g/L'           |         concentration   |      'g/L'     |           *1                |
|'mg/mL'         |         concentration   |      'g/L'     |           *1                |
|'µg/mL'         |         concentration   |      'g/L'     |          *1e-3              |
|'ng/mL'         |         concentration   |      'g/L'     |          *1e-6              |
|'mol/kg'        |         concentration   |    'mol/kg'    |          *1                 |
|'mmol/kg'       |         concentration   |    'mol/kg'    |          *1e-3              |
|'v/v %'         |         concentration   |    'v/v %      |          *1                 |
|'w/w %'         |         concentration   |    'w/w %'     |          *1                 |
|'v/w %'         |         concentration   |    'v/w %'     |          *1                 |
|'w/v %'         |         concentration   |    'w/v %'     |          *1                 |
|'U/ml'          |         concentration   |    'U/ml'      |          *1                 |
|'% saturated'   |         concentration   | '% saturated'  |          *1                 |
|'mL/min'        |      flowrate           |     'µl/s'     |        *(100/6)             |
|   'µl/s'       |      flowrate           |     'µl/s'     |          *1                 |
|   'nl/s'       |      flowrate           |     'µl/s'     |          *1e-3              |
| '%'(humidity)  |             humidity    |      '%'       |          *1                 |
| 'g/m^3'        |             humidity    |     'g/m^3'    |          *1                 |
| 'oz/y^3'       |             humidity    |     'g/m^3'    |         *3.7079776329e1     |
|      'kPa'     |       pressure          |      'kPa'     |          *1                 |
|    'Pa'        |      pressure           |      'kPa'     |           *1e-3             |
|    'MPa'       |        pressure         |      'kPa'     |          *1e3               |
| 'Bar'          |        pressure         |      'kPa'     |          *1e2               |
|  'mBar'        |       pressure          |      'kPa'     |          *1e-1              |
|  'atm'         |         pressure        |      'kPa'     |          *1.01325e2         |
|  'Torr'        |       pressure          |      'kPa'     |         *(101.325/760)      |
|  'PSI'         |       pressure          |      'kPa'     |          * 6.894757         |
|  'mmHg'        |      pressure           |      'kPa'     |         *1.33322387415e-1   |
| 'inchHg'       |      pressure           |      'kPa'     |          *3.38639           |
| 'seconds'      |       time              |    'seconds'   |          *1                 |
| 'nanoseconds'  |       time              |    'seconds'   |          *1e-9              |
| 'microseconds' |       time              |    'seconds'   |          *1e-6              |
| 'milliseconds' |       time              |    'seconds'   |          *1e-3              |
| 'minutes'      |       time              |    'seconds'   |           *6e1              |
| 'hours'        |       time              |    'seconds'   |          *3.6e3             |
| 'days'         |       time              |    'seconds'   |          *8.64e4            |
| 'kJ/mol'       |      energy             |     'kJ/mol'   |           *1                |
| 'kcal/mol'     |      energy             |     'kJ/mol'   |           *4.184            |
|  'µJ/s'        |       power             |       'µJ/s'   |            *1               |
|  'µcal/s'      |       power             |       'µJ/s'   |           *4.184            |
|'kilobytes (kB)'|      storage size       |'kilobytes (kB)'|           *1                |
|  'bytes (B)'   |      storage size       |'kilobytes (kB)'|           *1e-3             |
|'megabytes (MB)'|      storage size       |'kilobytes (kB)'|            *1e3             |
|'Gigabytes (GB)'|      storage size       |'kilobytes (kB)'|            *1e6             |
|'Terabytes (TB)'|      storage size       |'kilobytes (kB)'|            *1e9             |
|'kibibytes (KiB)'|     storage size       |'kilobytes (kB)'|        *((2^10)/1e3)        |
|'mebibytes (MiB)'|     storage size       |'kilobytes (kB)'|        *((2^20)/1e3)        |
|'gibibytes (GiB)'|     storage size       |'kilobytes (kB)'|        *((2^30)/1e3)        |
|'tebibytes (TiB)'|     storage size       |'kilobytes (kB)'|        *((2^40)/1e3)        |
|     'Å'        |      length             |       'nm'     |            *1e-1            |
|     'nm'       |      length             |       'nm'     |            *1               |
|     'μm'       |      length             |       'nm'     |            *1e3             |
|     'mm'       |     length              |       'nm'     |            *1e6             |
|     'cm'       |      length             |       'nm'     |            *1e7             |
|     'm'        |     length              |       'nm'     |            *1e9             |
|     'K'        |      temperature        |       'K'      |            *1               |
|     '°C'       |      temperature        |       'K'      |            +273.15          |
|     '°F'       |      temperature        |       'K'      | \*(5\9) - 32*(5\9) + 273.15  | 
