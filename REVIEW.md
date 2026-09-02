## 1. Sessiz Hata Yutma Sorunu

Except bloğu(71.-81. satır) her hatayı 200 + cevap olarak 0 döndürüyor. En geniş, kapsamlı sorun burada. Geçersiz para birimi, upstream 500, timeout, bozuk JSON bunların hepsi aynı yere düşüyor ve aynı sonucu veriyor.
Doğrulamak için attığım istek: http://localhost:8080/tools/convert?amount=250&from_=EUR&to=XYZ
Çıktı:

```json
{
  "amount": 250.0,
  "from": "EUR",
  "to": "XYZ",
  "rate": 0.0,
  "result": 0.0,
  "rate_date": "2026-09-02",
  "source": "ECB via frankfurter.dev"
}
```

## 2. Cache Tarihi Yok

Örneğin "EUR-JPY" bir kez sorulduktan sonra hangi tarih sorulursa sorulsun aynı kur-sonuç oranı dönüyor, ayrıca sorulan tarihle etiketlendiği için müşteriye yanlış bilgi veriliyor. Oluşturulan Cache için tarih eklenmemiş.
Örnek olarak aynı para birimlerine iki farklı tarihte istek attım:
http://localhost:8080/tools/convert?amount=250&from_=EUR&to=JPY&on=2026-08-28
http://localhost:8080/tools/convert?amount=250&from_=EUR&to=JPY&on=2026-01-15
Not: burada kodun beklediği on parametresini kullandım, çünkü cache'i test etmek için tarihin gerçekten işlenmesi gerekiyordu. Parametre adı uyuşmazlığı 5. maddede
Çıktı:

```json
{
  "amount": 250.0,
  "from": "EUR",
  "to": "JPY",
  "rate": 185.92,
  "result": 46480.0,
  "rate_date": "2026-08-28",
  "source": "ECB via frankfurter.dev"
}
```

```json
{
  "amount": 250.0,
  "from": "EUR",
  "to": "JPY",
  "rate": 185.92,
  "result": 46480.0,
  "rate_date": "2026-01-15",
  "source": "ECB via frankfurter.dev"
}
```

## 3. rate_date Kurun Gerçek Tarihini Göstermiyor

fetch_rate upstream'in cevabındaki date alanını hiç okumuyor çünkü "on or date.today()" olarak girilmiş. Hafta sonu sorusunda /latest'e düşüp cuma kurunu alıyor ve cumartesi diye gösteriyor.
Önce cumartesiye denk gelen bir tarihi parametre olarak verdim: http://localhost:8080/tools/convert?amount=250&from=EUR&to=USD&on=2026-08-29
Çıktı:

```json
{
  "amount": 250.0,
  "from": "EUR",
  "to": "USD",
  "rate": 1.16,
  "result": 290.0,
  "rate_date": "2026-08-29",
  "source": "ECB via frankfurter.dev"
}
```

Doğrulamak için Frankfurter Api istek attım: https://api.frankfurter.dev/v1/2026-08-29?base=EUR&symbols=USD
Çıktı:

```json
{
  "amount": 1.0,
  "base": "EUR",
  "date": "2026-08-28",
  "rates": { "USD": 1.1643 }
}
```

## 4. Çarpmadan Önce Yuvarlama Sorunu

convert api'si içerisindeki try bloğunda(60-61. satırlar) dönüştürme işleminde çarpmadan önce "round(rate, 2)" yuvarlama yapılmış, doğrudan para hatası oluşturur. Gerçek kurla 55.914.500 TL olması gerekirken servis 55.910.000 TL döndürüyor, 4.500 TL fark.
Attığım istek: http://localhost:8080/tools/convert?amount=1000000&from_=EUR&to=TRY
Çıktı:

```json
{
  "amount": 1000000.0,
  "from": "EUR",
  "to": "TRY",
  "rate": 55.91,
  "result": 55910000.0,
  "rate_date": "2026-09-02",
  "source": "ECB via frankfurter.dev"
}
```

Doğrulamak için attığım istek: https://api.frankfurter.dev/v1/latest?base=EUR&symbols=TRY
Çıktı:

```json
{
  "amount": 1.0,
  "base": "EUR",
  "date": "2026-09-02",
  "rates": { "TRY": 55.9145 }
}
```

## 5. Parametre adları README ile Uyuşmuyor

tool.py içerisinde 'from_' ve 'on' parametreleri verilmiş ama README dosyasında from ve date olarak belirtilmiş. Gönderilen URL hata vermeden sessizce varsayılanlara düşüyor. Örneğin birisi USD sorup EUR cevabı alabilir, girdiği tarih yerine bugünün tarihini alabilir.
Doğrulamak için attığım istek: http://localhost:8080/tools/convert?amount=250&from=USD&to=TRY&date=2026-08-28
Çıktı:

```json
{
  "amount": 250.0,
  "from": "EUR",
  "to": "TRY",
  "rate": 55.91,
  "result": 13977.5,
  "rate_date": "2026-09-02",
  "source": "ECB via frankfurter.dev"
}
```

## 6. Timeout ve Status Kontrolü Yok

client.get çağrılarında timeout parametresi yok, status yok(fetch_rate içerisinde 39. ve 40. satırlar). Upstream yavaşlarsa istek asılı kalır, 500 dönerse kod yine json() demeye devam eder. Model yanıt bekleyip asılı kaldığından müşteri yanıt alamıyor.

## 7. Hardcoded Upstream

Müşteriye zararı yok ama servis ağsız test edilemez. Bu yüzden testler gerçek API'ye bağımlı kalıyor, sahte upstream'e yönlendirilemiyor. Örneğin FX_UPSTREAM_BASE kapalı bir porta yönlendirilse bile kod yine gerçek API'ye gider.

## The one I would fix before shipping tonight

Bir numaralı bulgu: sessiz hata yutma. Diğerleri belirli senaryolarda yanlış sonuç verirken bu blok her hata sınıfını — geçersiz para birimi, upstream 500,
timeout, bozuk JSON — 200 + sıfır cevaba çeviriyor. Çağıran model hatayı hata olarak göremediği için müşteriye gerçek dışı bir sayı iletiyor.

## Things that look suspicious but are fine

Bir de şüpheli gördüğüm ama şu seviyede sorun olmayan bir bulgum var. Kur ve Dönüştürme mantığı aynı dosyalarda olmamalı her iş kendi dosyasında tanımlanıp çağırılmalı. Ama bu boyuttaki bir servis için makul, ayırmak müşteriye bir şey kazandırmaz.
