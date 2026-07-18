SELECT DISTINCT
    "Linha",
    "SOLICITAÇÕES",
    "AnoMês",
    UPPER(TRIM("UF")) AS "UF",
    UPPER(TRIM("Cidade")) AS "Cidade",
    UPPER(TRIM("TipoAtendimento")) AS "TipoAtendimento",
    UPPER(TRIM("Serviço")) AS "Serviço",
    UPPER(TRIM("Marca")) AS "Marca",
    UPPER(TRIM("Assunto")) AS "Assunto",
    UPPER(TRIM("Problema")) AS "Problema"
FROM "reclamacoes_contexto"
WHERE "Marca" IN (
    'CLARO',
    'DESKTOP',
    'NEXTEL',
    'STARLINK',
    'VIVO',
    'TIM',
    'OI'
)
AND "Ano" >= (SELECT MAX("Ano") - 2 FROM "reclamacoes_contexto");
