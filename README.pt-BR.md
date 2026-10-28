# ConstructCAD Components

[![Validate](https://github.com/francisreboucas/constructcad-components/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/francisreboucas/constructcad-components/actions/workflows/validate.yml)
[![Licença: CC BY 4.0](https://img.shields.io/badge/licen%C3%A7a-CC_BY_4.0-lightgrey.svg)](LICENSE)

Biblioteca gratuita de componentes paramétricos para o [ConstructCAD](https://github.com/francisreboucas/constructcad): mobiliário, marcenaria, louças e metais, dispositivos elétricos, iluminação e paisagismo, prontos para carregar em qualquer projeto.

[English](README.md) · [Catálogo](CATALOG.md) · [Como contribuir](CONTRIBUTING.md)

![A biblioteca inserida num projeto: mobiliário, marcenaria, louças, dispositivos elétricos e luminárias](docs/vitrine-3d.png)

## Usando um componente

1. Baixe um arquivo `.ccomp` de [`components/`](components) (veja todos no [catálogo](CATALOG.md)), ou a biblioteca inteira em ZIP pelo [release mais recente](https://github.com/francisreboucas/constructcad-components/releases/latest).
2. No ConstructCAD, carregue o arquivo: o componente e todos os seus tipos entram no projeto, junto com os materiais que faltarem.
   Pela linha de comando ou numa macro:

   ```sh
   ccad -p casa.ccad --save run component_load path=components/plumbing/pia-cozinha.ccomp
   ```

3. Insira com a ferramenta de componente, ou `component_place type="Pia cozinha 150 cm" position=[2,3]`.

Cada arquivo traz um componente com vários tipos (tamanhos). Os tipos compartilham a geometria e diferem nos valores dos parâmetros (`Largura`, `Profundidade`, `Altura`…), que você pode alterar depois de carregar.

## O que tem

| Pasta | Conteúdo |
|---|---|
| [`furniture`](components/furniture) | Mesas, cadeiras, camas, sofás, escrivaninhas, criados-mudos |
| [`casework`](components/casework) | Guarda-roupas, balcões e aéreos de cozinha, estantes |
| [`plumbing`](components/plumbing) | Bacias, lavatórios, pias, chuveiros, tanques, máquinas de lavar, banheiras, mictórios, bidês, caixas d'água, caixas de inspeção e de gordura |
| [`electrical`](components/electrical) | TUGs, TUEs, pontos de chuveiro, interruptores, quadros de distribuição, pontos de dados e TV |
| [`lighting`](components/lighting) | Plafons, pendentes, spots, luminárias lineares e arandelas |
| [`planting`](components/planting) | Árvores, coníferas, palmeiras, arbustos e vasos com planta para paisagismo |
| [`doors`](components/doors) | Portas de abrir de uma e duas folhas, pivotante, camarão, de vidro temperado, de correr simples e dupla, porta-janela de correr e portão basculante |
| [`windows`](components/windows) | Janelas de correr (também com veneziana), de abrir, maxim-ar, basculante e fixa |

As louças trazem as unidades Hunter de contribuição (NBR 8160) e os pesos relativos (NBR 5626), e os dispositivos elétricos o tipo e a potência em VA (NBR 5410), para o ConstructCAD dimensionar tubulações e circuitos.

## Como a biblioteca é gerada

Os componentes são escritos em JSON legível em [`sources/`](sources), no formato do comando `component_create` do motor. O [`tools/build.py`](tools/build.py) usa a própria linha de comando do ConstructCAD (`ccad`) para criar cada componente e salvá-lo como `.ccomp`; depois carrega cada arquivo num projeto novo para validá-lo e escreve o [`catalog.json`](catalog.json) e o [`CATALOG.md`](CATALOG.md). A CI roda a mesma verificação em cada pull request, com a versão fixada do ConstructCAD.

```sh
python tools/build.py --ccad caminho/do/ccad          # gera, valida e atualiza o catálogo
python tools/build.py --ccad caminho/do/ccad --check  # só verifica (CI)
```

Um `.ccomp` salvo pelo próprio app (`component_save`) também pode ser adicionado direto em `components/`, sem fonte JSON; ele é validado e catalogado do mesmo jeito.

As fontes de paisagismo são geradas: [`tools/vegetation.py`](tools/vegetation.py) cria cada espécie como malha (galhos por colonização do espaço, massas de folhas, frondes de palmeira) e escreve `sources/planting/`. Altere o gerador e rode-o antes do `build.py`, não o JSON.

## Compatibilidade

Formato `.ccomp` versão 1, gerado com o ConstructCAD 0.6.0. Os arquivos abrem no ConstructCAD 0.6.0 ou mais recente (portas e janelas exigem a 0.6.0; na 0.5.0 os demais componentes abrem sem os conectores).

## Licença

Os componentes estão sob a licença [Creative Commons Atribuição 4.0](LICENSE): use em qualquer projeto, comercial ou não; se redistribuir a biblioteca ou componentes derivados, dê o crédito a "ConstructCAD Components contributors".
