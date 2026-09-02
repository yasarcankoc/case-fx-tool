# fx-tool

Bir AI agent'ın çağırabileceği kur çevirme servisi. Kurlar
[Frankfurter](https://frankfurter.dev) üzerinden ECB verisinden geliyor.

## Çalıştırma

```bash
pip install -r requirements.txt
./run.sh
```

Ortam değişkenleri:

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `FX_UPSTREAM_BASE` | `https://api.frankfurter.dev` | Upstream adresi. Kodda hiçbir yerde sabit host yok. |
| `PORT` | `8080` | Servisin dinlediği port. |

## Testler

```bash
./test.sh
```

Testler upstream'i sahteler, ağ gerektirmez:

```bash
FX_UPSTREAM_BASE=http://127.0.0.1:9 ./test.sh
```

## Endpoint
```
GET /tools/convert?amount=250&from=EUR&to=TRY&date=2026-08-28
```

`date` isteğe bağlı, verilmezse en güncel kur kullanılır.

Başarılı cevap:

```json
{
  "amount": 250,
  "from": "EUR",
  "to": "TRY",
  "rate": 47.1234,
  "result": 11780.85,
  "rate_date": "2026-08-28",
  "asked_date": "2026-08-28",
  "source": "ECB via frankfurter.dev"
}
```

`rate_date` kurun gerçekten ait olduğu gündür ve upstream'in cevabından okunur.
`asked_date` çağıranın sorduğu gündür. İkisi farklı olabilir; model müşteriye
kurun hangi güne ait olduğunu bu sayede söyleyebilir.

## Hata kodları

Hatalar non-2xx status ile şu biçimde döner:

```json
{ "error": "invalid_amount", "message": "Tutar sıfırdan büyük olmalı." }
```

| Kod | HTTP | Ne zaman |
|---|---|---|
| `invalid_amount` | 400 | Tutar sıfır, negatif veya ikiden fazla ondalık basamaklı |
| `unknown_currency` | 400 | Para birimi kodu üç harf değil ya da ECB'de yok |
| `date_out_of_range` | 400 | Tarih gelecekte veya 1999-01-04 öncesinde |
| `upstream_unavailable` | 502 | Upstream'e ulaşılamıyor, zaman aşımı veya 5xx |
| `upstream_invalid_response` | 502 | Upstream'den JSON gelmiyor ya da beklenen alanlar eksik |

Tarih biçimi bozuksa FastAPI 422 döndürür.

## Durum bazında davranış

**Hafta sonu ve tatil.** ECB o günler kur yayınlamaz. Upstream en yakın önceki
iş gününün kurunu döndürür ve hangi güne ait olduğunu cevabında bildirir. Servis
bu tarihi `rate_date` olarak aynen geçirir, `asked_date` ise sorulan gün kalır.
İstek reddedilmez ama kurun tarihi hiçbir zaman gizlenmez.

**Gelecek tarih veya 1999 öncesi.** `date_out_of_range` ile reddedilir. Upstream'e
gidilmez.

**Geçersiz para birimi.** Üç harf değilse istek upstream'e hiç gitmez. ECB'de
karşılığı yoksa upstream 404 döner ve `unknown_currency` olarak çevrilir. Hiçbir
durumda sıfır veya uydurma kur dönmez.

**`from` ve `to` aynı.** Kur tanımı gereği 1.0'dır ve upstream'e sorulmaz.
`rate_date` sorulan tarihe eşittir, çünkü bu kur ECB yayınına bağlı değildir.

**Upstream yavaş, 500 dönüyor veya JSON değil.** Beş saniyelik zaman aşımı var.
Bağlantı hatası, zaman aşımı ve 5xx `upstream_unavailable`; ayrıştırılamayan
veya eksik alanlı cevap `upstream_invalid_response` olur. İkisi de 502 döner,
başarılı cevap taklidi yapılmaz.

**Tutar eksik, sıfır, negatif veya çok ondalıklı.** `invalid_amount` ile
reddedilir. Eksikse FastAPI 422 verir.

## Cache

Tarihli sorgular süresiz cache'lenir; ECB geçmiş bir günün kurunu bir daha
değiştirmez. Anahtar `(from, to, date)` üçlüsüdür. Tarihsiz (`latest`) sorgular
cache'lenmez, çünkü gün içinde güncellenebilirler.