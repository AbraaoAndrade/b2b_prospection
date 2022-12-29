# b2b_prospection

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://https://abraaoandrade-b2b-prospection-b2b-prospection-app-tt1db1.streamlit.app)

## Contextualização

A prospecção comercial é o primeiro passo para a venda. Esse tipo de atividade é fundamental para construção de um bom volume de negócios, portanto, mapear a praça em que sua empresa está inserida é inerente a um bom planejamento estratégico de vendas.

## Projeto
O projeto se propõe a gerar um relatório de potenciais clientes, com informações de localização e telefone a partir de ferramentas disponíveis de Ciência de Dados.

Para isso foi utilizada a API Places, um serviço da Google que retorna informações sobre lugares usando solicitações HTTP. Essa API permite pesquisar estabelecimentos por tipo, como farmácia, bar, padaria, …, dentro de um raio a partir de uma coordenada de referência.

Acontece que há um limite de 60 resultados por requisição na API, por isso, a ideia é fragmentar sua região de interesse em sub-regiões para otimizar o número de estabelecimentos gerado. No exemplo abaixo, foi realizada uma prospecção de farmácias em Natal-RN. Para isso a cidade foi subdividida em circulos com raio de 900 metros, resultando em 59 subregiões.

![alt text](https://github.com/AbraaoAndrade/b2b_prospection/blob/main/images/processo.png)

O gráfico de barras abaixo mostra o número de resultados retornados por subregião. O objetivo desse plot é mostrar o grau de eficiência da segmentação. O ideal é que as barrinhas estejam o mais próximo possível do número máximo de resultados, 60.

![alt text](https://raw.githubusercontent.com/AbraaoAndrade/b2b_prospection/main/images/plot.png)

Com a lista de estabelecimentos gerada, o último passo é usar a mesma API para adicionar os detalhes importantes, como telefone e horário de funcionamento.

------

Nesse projeto foi utilizada a API Places, um serviço da Google em que as interações se dão mediante uma chave de API, portanto, para experimentar o App será necessário criar uma chave (https://developers.google.com/maps/documentation/places/web-service/get-api-key).