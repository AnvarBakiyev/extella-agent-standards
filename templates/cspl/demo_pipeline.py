# -*- coding: utf-8 -*-
"""Конвейер из языков, которые не могут вызвать друг друга.

SQL → C → Go → Rust → slide. Пять звеньев, пять разных языков; ни одно не знает
об остальных. Совместимыми их делает не общий рантайм, а общий ДОГОВОР:
JSON на входе, JSON на выходе. Это и есть смысл подложки — N языков вместо
N×N мостов между ними.
"""
from __future__ import annotations
import copy, json, pathlib, sqlite3, tempfile

from handler_sql import run_expert as sql_run, DEFAULT_POLICY as SQL_POLICY
from handler_native import run_expert as native_run, DEFAULT_POLICY as NATIVE_POLICY
from handler_slide import run_expert as slide_run, DEFAULT_POLICY as SLIDE_POLICY

# ── эксперты, каждый на своём языке ──────────────────────────────────────────

ЭКСПЕРТ_SQL = "SELECT name, amount FROM clients WHERE amount > 0"

ЭКСПЕРТ_C = r"""
/* Считает итог и среднее. Читает JSON из ввода, пишет JSON в вывод. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
int main(void){
    char буфер[1<<16]; size_t n = fread(буфер,1,sizeof(буфер)-1,stdin); буфер[n]='\0';
    double сумма=0; int штук=0; char *p=буфер;
    while((p=strstr(p,"\"amount\":"))){ p+=9; сумма+=atof(p); штук++; }
    printf("{\"total\":%.0f,\"count\":%d,\"avg\":%.0f}", сумма, штук, штук?сумма/штук:0);
    return 0;
}
"""

ЭКСПЕРТ_GO = r"""
// Проверяет итог на правдоподобие и добавляет вывод словами.
package main
import ("encoding/json";"fmt";"os")
func main(){
    var вход map[string]any
    json.NewDecoder(os.Stdin).Decode(&вход)
    итог, _ := вход["total"].(float64)
    штук, _ := вход["count"].(float64)
    вердикт := "в пределах ожидаемого"
    if итог > 1000000 { вердикт = "долг превышает миллион — нужен разбор" }
    if штук == 0 { вердикт = "должников нет" }
    вход["verdict"] = вердикт
    out, _ := json.Marshal(вход)
    fmt.Print(string(out))
}
"""

ЭКСПЕРТ_RUST = r"""
// Округляет и готовит подписи. Разбор устойчив к пробелам: договор допускает
// любой JSON, а не только плотный — на этом конвейер и спотыкался.
use std::io::Read;
fn main(){
    let mut s=String::new(); std::io::stdin().read_to_string(&mut s).unwrap();
    let итог = число(&s,"total");
    let среднее = число(&s,"avg");
    let вердикт = строка(&s,"verdict");
    println!("{{\"total_mln\":\"{:.2}\",\"avg_ths\":\"{:.0}\",\"verdict\":\"{}\"}}",
             итог/1_000_000.0, среднее/1000.0, вердикт);
}
fn после_ключа<'a>(s:&'a str, ключ:&str)->Option<&'a str>{
    let метка=format!("\"{}\"",ключ);
    s.find(&метка).map(|i|{ let x=&s[i+метка.len()..];
        x.trim_start().strip_prefix(':').unwrap_or(x).trim_start() })
}
fn число(s:&str,ключ:&str)->f64{
    после_ключа(s,ключ).map(|x|{
        x.chars().take_while(|c| c.is_ascii_digit()||*c=='.'||*c=='e'||*c=='E'||*c=='+'||*c=='-')
         .collect::<String>().parse().unwrap_or(0.0)}).unwrap_or(0.0)
}
fn строка<'a>(s:&'a str,ключ:&str)->&'a str{
    match после_ключа(s,ключ){
        Some(x)=>{ let x=x.strip_prefix('"').unwrap_or(x);
                   match x.find('"'){Some(j)=>&x[..j],None=>""} },
        None=>"" }
}
"""

def ЭКСПЕРТ_SLIDE(данные: dict) -> str:
    return f"""# Долги клиентов

## Итог по базе
!число {данные['total_mln']} | миллиона тенге всего долга
!число {данные['avg_ths']} | тысяч тенге в среднем на клиента

## Вывод
- {данные['verdict']}
> Собрано конвейером: SQL, C, Go, Rust, язык слайдов
"""

def взять(шаг: dict, имя: str) -> dict:
    """Звено конвейера обязано отдать результат — иначе конвейер честно встаёт."""
    if not шаг.get("ok"):
        беда = шаг.get("error") or {}
        raise SystemExit(f"Конвейер остановлен на звене «{имя}»: "
                         f"{беда.get('code')} — {беда.get('message','')[:200]}")
    return шаг["result"]


# ── прогон ───────────────────────────────────────────────────────────────────

with tempfile.TemporaryDirectory() as врем:
    база = str(pathlib.Path(врем) / "к.db")
    с = sqlite3.connect(база)
    с.execute("CREATE TABLE clients (name TEXT, amount REAL)")
    с.executemany("INSERT INTO clients VALUES (?,?)",
                  [("ТОО Астра",1250000),("ИП Ким",340000),("ТОО Байт",90000),("ТОО Ноль",0)])
    с.commit(); с.close()

    полная = copy.deepcopy(NATIVE_POLICY)
    полная["scope"]["allowedLanguages"] = ["c","go","rust"]

    print("1. cspl=sql   — достать данные")
    ш1 = sql_run(ЭКСПЕРТ_SQL, {}, база, SQL_POLICY)
    print("   строк:", ш1["result"]["count"], "|", ш1["planHash"][:22])

    print("2. cspl=c     — посчитать")
    ш2 = native_run("c", ЭКСПЕРТ_C, {"rows": взять(ш1,"sql")["rows"]}, полная)
    print("   ", ш2.get("result") or ш2.get("error"), "| сборка", ш2.get("receipt",{}).get("buildSeconds"), "с")

    print("3. cspl=go    — проверить и озвучить")
    ш3 = native_run("go", ЭКСПЕРТ_GO, взять(ш2,"c"), полная)
    print("   ", ш3.get("result") or ш3.get("error"), "| сборка", ш3.get("receipt",{}).get("buildSeconds"), "с")

    print("4. cspl=rust  — округлить для показа")
    ш4 = native_run("rust", ЭКСПЕРТ_RUST, взять(ш3,"go"), полная)
    print("   ", ш4.get("result") or ш4.get("error"), "| сборка", ш4.get("receipt",{}).get("buildSeconds"), "с")

    print("5. cspl=slide — нарисовать")
    тёмная = copy.deepcopy(SLIDE_POLICY); тёмная["theme"]="dark"; тёмная["footer"]="Extella · конвейер языков"
    ш5 = slide_run(ЭКСПЕРТ_SLIDE(взять(ш4,"rust")), {}, тёмная)
    print("   слайдов:", ш5["result"]["slides"], "| байт:", ш5["result"]["bytes"])
    pathlib.Path("конвейер.html").write_text(ш5["result"]["html"], encoding="utf-8")

    print("\nотпечатки звеньев:")
    for имя, ш in (("sql",ш1),("c",ш2),("go",ш3),("rust",ш4),("slide",ш5)):
        print(f"   {имя:6} {ш['planHash'][:30]}  ok={ш['ok']}")
    print("\nсохранено: конвейер.html")
