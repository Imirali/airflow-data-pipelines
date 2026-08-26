SET NOCOUNT ON

declare @sf varchar(30), @nomzak varchar(30), @docid integer

set @sf = 'ФА26-544366'

select @nomzak = sih.[Order No_] 
from NAV.dbo.[Юнидент$Sales Invoice Header] sih
where No_ = @sf

select @docid = id
from sharezakaz
where nomzak = (@nomzak + '/1')

-- Создаём временную таблицу с количеством для каждой партии
select 
    kodtov,
    count(*) as kolvo,
    (select count(*) from sgtins sg2 where sg2.kodtov = sg.kodtov) as total_batches,
    batch,
    expiration_date,
    gtin
into #batches
from sgtins sg
where barcode in (
    select barcode
    from inventoryflow
    where docid = @docid and doctype = 1
)
group by kodtov, batch, expiration_date, gtin

-- Основной запрос
select 
    left(sih.[Order No_], 20) as NZAKAZA,
    left(sih.[No_], 20) as DCODE,
    cast(sih.[Posting Date] as datetime) as DATE_DOC,
    left(sil.No_, 11) as CODE,
    left(i.[Full Description], 100) as PRODUCT,
    left(md.Name, 50) as NAME_PRO,
    left(md.[Страна], 50) as COUNTRY,
    b.kolvo as KOLVO,
    left(sil.[Unit of Measure Code], 20) as EI,
    round(sil.[Qty_ per Unit of Measure], 10, 1) as KOL_PACK,
    round(sil.[Net Weight], 10, 8) as VES,
    round(sil.[Unit Volume], 10, 3) as VOLUME,
    left('', 50) as TEMP,
    left('', 13) as EAN13,
    round((sil.[Amount Including VAT] * isnull(ex.[Relational Exch_ Rate Amount], 1)), 10, 2) / nullif(sil.Quantity, 0) as PRICE_NDS,
    round(0, 10, 2) as CENO_Z,
    left('', 50) as PRPRCS,
    cast(isnull(replace(sil.[VAT Identifier], 'НДС', ''), '0') as integer) as NDS,
    -- 
    round((sil.[Amount Including VAT] * isnull(ex.[Relational Exch_ Rate Amount], 1)) * (b.kolvo / sil.Quantity), 10, 2) as SUMMA,
    -- 
    round((sil.Amount * isnull(ex.[Relational Exch_ Rate Amount], 1) * (isnull([VAT %], 0) / 100.0)) * (b.kolvo / sil.Quantity), 10, 2) as SUM_NDS,
    case when r.[CD No_] = '-' then '' else r.[CD No_] end as GTD,
    left('', 100) as ORG_SERT,
    left(i.[Сертификат], 100) as SERT_N,
    cast(i.[Sertificat] as datetime) as DAT_SERT,
    left('', 100) as DECL,
    left(b.batch, 50) as SERIES,
    null as DZ,
    cast(b.expiration_date as datetime) as SROK_S,
    0 as GV,
    1 as MARKTAG,
    '00000000175188' as PLACEID,
    1 as ACCEPT,
    null as DTPROIZ,
    left(b.gtin, 14) as GTIN,
    left(sih.[No_], 20) as NSF,
    cast(sih.[Posting Date] as datetime) as DSF
from NAV.dbo.[Юнидент$Sales Invoice Header] sih
left join NAV.dbo.[Юнидент$Sales Invoice Line] sil on sil.[Document No_] collate Cyrillic_General_CS_AS = sih.[No_] collate Cyrillic_General_CS_AS
left join NAV.dbo.[Юнидент$Item] i on i.No_ collate Cyrillic_General_CS_AS = sil.No_ collate Cyrillic_General_CS_AS
left join NAV.dbo.[Юнидент$Manufacturer Dimension] md on md.[Dimension Value] collate Cyrillic_General_CS_AS = i.[Global Dimension 2 Code] collate Cyrillic_General_CS_AS
left join NAV.dbo.[Юнидент$Currency Exchange Rate] ex on ex.[Starting Date] = sih.[Posting Date] and ex.[Currency Code] collate Cyrillic_General_CS_AS = sih.[Currency Code] collate Cyrillic_General_CS_AS
left join NAV.dbo.[Юнидент$Custom Declaration Relation] r on r.[Document No_] collate Cyrillic_General_CS_AS = sih.No_ collate Cyrillic_General_CS_AS and r.[Line No_] = sil.[Line No_]
left join NAV.dbo.[Юнидент$Custom Declaration Line] ll on ll.[CD No_] collate Cyrillic_General_CS_AS = r.[CD No_] collate Cyrillic_General_CS_AS and ll.[CD Line No_] = r.[CD Line No_]
join #batches b on b.kodtov = sil.No_
where sih.No_ = @sf

drop table #batches