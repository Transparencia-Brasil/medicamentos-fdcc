# Diagnóstico inicial: compras de medicamentos no DF

## Pergunta de trabalho

**Quem comprou o que, de quem, por quanto, quando e como?** Este estudo usa o CSV exportado do PNCP para selecionar contratações e testa o endpoint [`GET /modulo-ocds/1_releases`](https://dadosabertos.compras.gov.br/swagger-ui/index.html) para examinar as releases OCDS. O [manual da API](https://www.gov.br/compras/pt-br/acesso-a-informacao/manuais/manual-dados-abertos/manual-api-compras.pdf), seção 14, documenta os filtros `buyerID`, `releaseStartDate`, `releaseEndDate`, `page` e `offset`. O link que funcionou no navegador usa a grafia **`offSet`**; o código preserva essa grafia.

O objetivo deste notebook é **consultar e salvar o JSON bruto para validar a cobertura**, não produzir ainda uma tabela final de medicamentos e fornecedores.

## Dados do CSV e três casos de teste

O [CSV](inputs/consulta-contratacoes-20260930162835.csv) tem 1.515 contratações, 55 colunas e 1.515 números PNCP distintos. Todas as unidades compradoras estão no DF, mas apenas 320 registros são da esfera **Distrital**; 1.084 são federais. Uma triagem textual no objeto encontrou 104 **candidatos** a medicamento entre os distritais. Isso não substitui a classificação dos itens: há falsos positivos e falsos negativos.

O notebook [testes-api.ipynb](testes-api.ipynb) usa três linhas verificadas no CSV:

| Caso | Número PNCP | Comprador (`buyerID`) | Publicação no CSV | Por que testar |
| --- | --- | --- | --- | --- |
| 1 | `00394700000108-1-000411/2026` | SES/DF `00394700000108` | 30/09/2026 | Misoprostol, pregão; o CSV ainda não indica resultado. Reproduz o link fornecido. |
| 2 | `08942610000116-1-000084/2026` | PMDF `08942610000116` | 28/07/2026 | Insulina FIASP, dispensa; o CSV indica resultado. |
| 3 | `00394700000108-1-000151/2026` | SES/DF `00394700000108` | 14/04/2026 | Estradiol, pregão para demanda judicial; o CSV indica resultado. |

Em cada teste, `buyerID`, `releaseStartDate` e `releaseEndDate` são declarados manualmente. A função `executar_teste` confere o CNPJ e a data de publicação com a linha do CSV, mostra a URL e **salva o JSON bruto da página**. O retorno também permanece em `resposta_1`, `resposta_2` ou `resposta_3` para exploração no notebook. `page=1` e `offSet=10` são os valores iniciais. Uma página pode conter várias contratações do mesmo comprador; a presença da linha escolhida deve ser verificada pelos identificadores retornados. Se ela não aparecer, testar páginas seguintes ou ampliar o intervalo.

Cada execução salva imediatamente `output/resposta_1.json`, `output/resposta_2.json` ou `output/resposta_3.json`. A pasta é criada se necessário; repetir um teste substitui seu arquivo. Os JSONs são ignorados pelo `.gitignore` para evitar incluir respostas volumosas no projeto por acidente.

## Leitura dos resultados

| Pergunta | Onde procurar na release | Limite a verificar |
| --- | --- | --- |
| Quem comprou? | `buyer`, `parties` | Conferir CNPJ/identificador e nome contra o CSV. |
| O que? | `tender.items` e eventuais `awards.items` | Confirmar medicamento, apresentação, quantidade e vínculo do item ao prêmio. |
| De quem? | `awards.suppliers`/`parties` | Fornecedor vencedor não é necessariamente fabricante. |
| Por quanto? | `tender.value`/itens e `awards.value`/itens, se presentes | Não atribuir total da contratação a um medicamento nem chamar estimativa de lance. |
| Quando? | Datas da release e da adjudicação, se presentes | O filtro `releaseStartDate`/`releaseEndDate` é de **publicação**. Não equivale automaticamente à data de homologação. |
| Como? | `tender.procurementMethod` e campos correlatos; modalidade no CSV | Demanda judicial é motivação/contexto, não modalidade. |

Esses caminhos são **pontos de inspeção**, não confirmação de que todos os campos estejam preenchidos na implementação da API. A release pode representar uma etapa do processo; homologação, contrato, entrega e pagamento são eventos distintos. É preciso examinar respostas reais antes de definir chaves, cardinalidades e indicadores finais.

