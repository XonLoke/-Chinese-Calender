# Comprehensive Lunar Cross-Validation Results

**Date:** 2026-06-10
**Engine:** chinese_calendar v<module 'chinese_calendar._version' from 'D:\\c_wannianli\\chinese_calendar\\_version.py'>
**Reference:** lunar_python (6tail)

---

## Results

| Category | Total | Exact | % | ±1 day | Major Error |
|----------|-------|-------|---|--------|-------------|
| Random dates (1900-2100) | 500 | 492 | 98.4% | 1 | 7 |
| Spring Festival (1900-2100) | 201 | 199 | 99.0% | — | 2 |
| Known leap years | 5 | 2 | — | — | 3 |
| Edge dates | 453 | 445 | 98.2% | — | 8 |


## Random Date Errors

- 1922-08-02: engine=(1922,6,10,True) lunar_python=(1922,6,10,False)
- 1922-08-15: engine=(1922,6,23,True) lunar_python=(1922,6,23,False)
- 1976-12-21: engine=None, lunar_python=1976-11-1
- 1993-04-25: engine=(1993,4,4,False) lunar_python=(1993,3,4,True)
- 1995-09-27: engine=(1995,9,3,False) lunar_python=(1995,8,3,True)
- 2020-06-05: engine=(2020,5,14,False) lunar_python=(2020,4,14,True)
- 2047-07-25: engine=(2047,6,3,True) lunar_python=(2047,6,3,False)

## Spring Festival Errors

- 1916: Spring Festival solar=1916-02-03, engine gave (1915,12,30)
- 1985: Spring Festival solar=1985-02-20, engine gave (1985,2,1)

## Edge Date Errors

- 1916-02-29: engine=(1916,1,26) lp=(1916,1,27)
- 1984-12-31: engine=(1984,12,10) lp=(1984,11,10)
- 1985-01-01: engine=(1984,12,11) lp=(1984,11,11)
- 2014-12-31: engine=(2014,12,10) lp=(2014,11,10)
- 2015-01-01: engine=(2014,12,11) lp=(2014,11,11)
- 2033-12-31: engine=(2033,12,10) lp=(2033,11,10)
- 2034-01-01: engine=(2033,12,11) lp=(2033,11,11)
- 1582-10-04: engine=(1582,9,8) lp=(1582,9,18)
