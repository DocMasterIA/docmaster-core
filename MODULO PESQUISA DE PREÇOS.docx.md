**📌 MÓDULO: PESQUISA DE PREÇOS – DOCMASTER IA**

**ESPECIFICAÇÃO TÉCNICA PARA DESENVOLVIMENTO**

---

**1\. OBJETIVO DO MÓDULO**

Implementar um sistema automatizado de **pesquisa de preços com uso de IA**, integrado ao PNCP, capaz de:

* Buscar preços reais de contratações públicas; 

* Selecionar automaticamente **3 cotações válidas por item**; 

* Gerar **relatório técnico completo** conforme boas práticas e Lei nº 14.133/2021; 

* Permitir **intervenção humana (modo assistido)**; 

* Exportar resultados em formato técnico e simplificado (Excel). 

---

**2\. FLUXO DO USUÁRIO (UX)**

**2.1 Entrada de dados**

O sistema deve permitir 3 formas de entrada:

**a) Cadastro manual**

Campos mínimos por item:

* descrição do item (texto livre) 

* unidade de medida (opcional) 

* quantidade (opcional) 

**b) Importação por planilha (Excel)**

* botão: **“Importar itens”** 

* layout padrão: 

  * coluna A: descrição 

  * coluna B: unidade 

  * coluna C: quantidade 

**c) Download de modelo**

* botão: **“Baixar planilha modelo”** 

---

**2.2 Definição de faixa de preço**

Opcional por item:

* valor mínimo 

* valor máximo 

Se não informado:

* sistema define automaticamente com base nos dados encontrados 

---

**2.3 Execução da pesquisa**

Dois modos:

**a) Modo em lote**

* processa todos os itens simultaneamente 

**b) Modo individual**

* usuário executa item por item 

---

**3\. INTEGRAÇÃO COM PNCP**

**3.1 Fonte de dados**

* API oficial do PNCP 

**3.2 Campos obrigatórios a capturar**

Para cada item encontrado:

* descrição do item 

* unidade de medida 

* quantidade 

* valor unitário 

* órgão/entidade 

* município/UF 

* número do processo/licitação 

* data de atualização 

* critério de julgamento 

* existência de resultado (true/false) 

* atas/contratos vinculados 

**3.3 Campos adicionais (enriquecimento)**

* categoria do item 

* código do catálogo 

* NCM/NBS 

* informação complementar 

---

**4\. MOTOR DE BUSCA (LÓGICA)**

**4.1 Busca híbrida (OBRIGATÓRIA)**

A busca NÃO deve ser apenas textual.

Combinar:

* similaridade semântica (IA) (ESPECIFICADO NO DOC. **módulo de normalização semântica e conversão de unidades)**

* palavras-chave da descrição 

* unidade de medida 

* categoria do item 

* natureza (material/serviço) 

* faixa de preço (quando informada) 

---

**4.2 Estratégia de busca**

Para cada item:

1. Buscar correspondência exata 

2. Se não houver: 

   * buscar correspondência aproximada (similaridade semântica) 

3. Se ainda insuficiente: 

   * expandir busca por categoria 

4. Aplicar filtro de faixa de preço (se houver) 

5. Aplicar filtro de recência (priorizar dados recentes) 

---

**4.3 Fallback automático**

Quando não houver resultados ideais:

* aceitar descrições similares 

* ignorar faixa de preço parcialmente 

* priorizar consistência sobre exatidão textual 

---

**5\. CLASSIFICAÇÃO DAS COTAÇÕES (IA)**

**5.1 Critérios de avaliação**

Cada resultado deve ser analisado com base em:

* compatibilidade da descrição 

* compatibilidade da unidade 

* aderência ao objeto 

* natureza do item 

* recência da contratação 

* consistência dos dados 

* coerência do valor 

---

**5.2 Score interno (NÃO EXIBIR)**

A IA deve gerar score interno:

* verde (alto) 

* amarelo (médio) 

* vermelho (baixo) 

⚠️ REGRA:

* **NÃO exibir score no relatório final** 

* uso exclusivo interno para seleção 

---

**6\. SELEÇÃO DAS COTAÇÕES**

Para cada item:

* selecionar **exatamente 3 cotações** 

* priorizar: 

  1. maior compatibilidade 

  2. dados mais recentes 

  3. diversidade de fontes (evitar duplicidade de órgão) 

---

**7\. MODO MANUAL ASSISTIDO**

Após a seleção automática:

Usuário pode:

* visualizar cotações sugeridas 

* rejeitar qualquer cotação 

* substituir por outra opção da lista 

Sistema deve:

* manter histórico da alteração 

* recalcular média automaticamente 

---

**8\. PROCESSAMENTO FINAL**

Para cada item:

* armazenar: 

  * 3 valores selecionados 

  * média aritmética 

---

**9\. RELATÓRIO TÉCNICO COMPLETO**

**Estrutura obrigatória:**

**1\. Identificação**

* órgão 

* objeto 

* data 

* responsável 

**2\. Metodologia**

* uso do PNCP 

* busca automatizada por IA 

**3\. Análise técnica**

* critérios utilizados 

**4\. Quadro resumo**

* item 

* 3 cotações 

* média 

**5\. Detalhamento**

* origem de cada cotação: 

  * órgão 

  * processo 

  * data 

  * valor 

**6\. Análise de risco**

* inconsistências detectadas 

* nível de confiabilidade geral (texto) 

**7\. Conclusão**

Texto padrão obrigatório:

“As cotações selecionadas foram obtidas mediante consulta ao PNCP, sendo escolhidas com base na compatibilidade da descrição, unidade de medida, natureza do objeto, recência da contratação e consistência dos dados disponíveis.”

---

**10\. MODO AUDITORIA**

Versão alternativa do relatório contendo:

* fundamentação na Lei nº 14.133/2021 

* justificativa da metodologia 

* explicação técnica da escolha das cotações 

* linguagem voltada para TCM/TCU 

---

**11\. RELATÓRIO RESUMIDO (EXCEL)**

Gerar arquivo contendo apenas:

* nome do item 

* cotação 1 

* cotação 2 

* cotação 3 

* média 

⚠️ NÃO incluir:

* dados brutos 

* itens descartados 

* score 

---

**12\. REGRAS DE NEGÓCIO IMPORTANTES**

**12.1 NÃO utilizar dados do PCA**

Remover completamente:

* valor planejado 

* categoria do PCA 

* comparação planejado x contratado 

---

**12.2 Normalização de dados**

Antes da análise:

* padronizar descrições 

* padronizar unidades 

* tratar duplicidades 

---

**12.3 Atualização de dados**

* implementar sincronização incremental com PNCP 

* usar campo: dataAtualizacao 

---

**13\. ARQUITETURA SUGERIDA**

**Backend**

* API PNCP (integração) 

* Motor de busca híbrido 

* Motor de classificação IA 

* Módulo de seleção 

* Gerador de relatório 

**Frontend**

* Tela de cadastro/importação 

* Tela de execução 

* Tela de validação (modo assistido) 

* Tela de relatório 

---

**14\. FLUXO RESUMIDO DO SISTEMA**

1. Usuário insere itens 

2. Define faixa de preço (opcional) 

3. Sistema consulta PNCP 

4. IA classifica resultados 

5. Sistema seleciona 3 cotações 

6. Usuário pode ajustar (modo assistido) 

7. Sistema calcula média 

8. Gera relatório técnico 

9. Exporta Excel resumido

