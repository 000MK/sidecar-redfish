# README #

`inrow-cdu`專屬的測試。通常是因為hardware配置不同，導致操作不同。  

## TestCase
### Pump
1. 共2個pump。
2-1. 當轉速>0時，兩個pump轉速必須設為一致(即：pump1_speed=30, pump2_speed=30，才是合法的)。
2-2. 當轉速=0時，代表pump停止，兩個pump轉速可以不一致(即：pump1_speed=0, pump2_speed=50，是合法的)。

Script:
```
--
1-1) pump1,2停止，pump1,2轉速須為0
--
2-1) pump1轉速設為35，pump1轉速須為35，pump2轉速須為0
2-2) pump1轉速設為70，pump1轉速須為70，pump2轉速須為0
2-3) pump1停止，pump1轉速須為0，pump2轉速須為0
--
3-1) pump2轉速設為35，pump1轉速須為0，pump2轉速須為35
3-2) pump2轉速設為70，pump2轉速須為70，pump2轉速須為0
3-3) pump2停止，pump1轉速須為0，pump2轉速須為0
--
4-1) pump1轉速設為35，pump1轉速須為35，pump2轉速須為0
4-2) pump2轉速設為70，pump1,2轉速須為70
4-3) pump2轉速設為35，pump1,2轉速須為35
--
5-1) pump1停止，pump1轉速須為0，pump2轉速須為35
5-2) pump2停止，pump1轉速須為0，pump2轉速須為0
--
(註) 只要pump1開，則 ev1,2全開；pump1關，則 ev1,2全關；pump2同理。
```


