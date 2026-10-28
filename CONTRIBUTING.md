# Como contribuir · Contributing

Contribuições de componentes são muito bem-vindas. *Component contributions are very welcome; the rules below apply in any language.*

## Duas formas de enviar um componente

**1. Fonte JSON (preferida).** Crie `sources/<pasta>/<nome-do-arquivo>.json`:

```json
{
  "component": "Nome do componente",
  "def": {
    "kind": "Furniture",
    "params": [{ "name": "Largura", "value": 1.2, "kind": "Length", "instance": false }],
    "items": [
      {
        "name": "Tampo",
        "material": "Madeira",
        "in_plan": true,
        "shape": { "Box": { "x": "-Largura / 2", "y": "-0.4", "z": "0.72", "width": "Largura", "depth": "0.8", "height": "0.03" } }
      }
    ]
  },
  "types": [
    { "name": "Nome do tipo 120", "values": {}, "info": { "description": "…" } },
    { "name": "Nome do tipo 160", "values": { "Largura": 1.6 }, "info": { "description": "…" } }
  ],
  "materials": [{ "name": "Granito", "color": [70, 70, 75] }]
}
```

`def` tem a mesma forma do `params.def` que o `type_get` do ConstructCAD mostra; as peças (`Box`, `Cylinder`, `Extrusion`, `Profile`, `Revolution`) e as expressões estão descritas no comando [`component_create`](https://github.com/francisreboucas/constructcad/blob/main/docs/commands.md#component_create). `materials` só é preciso para materiais que o template do ConstructCAD não tem (Alvenaria, Reboco, Concreto, Madeira, Vidro, Gesso, Telha cerâmica, Contrapiso, Tecido, Louça, Aço, PVC).

Depois rode `python tools/build.py --ccad caminho/do/ccad` e inclua no commit a fonte, o `.ccomp` gerado e o catálogo atualizado.

**2. Arquivo salvo pelo app.** Modele o componente no editor do ConstructCAD, salve-o como arquivo (`component_save`) em `components/<pasta>/`, rode o build para validar e atualizar o catálogo, e envie. Prefira a fonte JSON quando puder: ela é mais fácil de revisar.

## Convenções

- **Pastas**: `furniture`, `casework`, `plumbing`, `electrical`, `lighting`, `planting`, `doors`, `windows`. Arquivos em minúsculas com hífens, sem acentos: `pia-cozinha.json`.
- **Origem e eixos**: metros; origem no ponto de inserção, X para a direita, Y para o fundo (a parede), Z para cima. Móveis e louças centrados na origem, com o lado encostado à parede em +Y. Dispositivos de parede ocupam `y` de `-Profundidade` a `0` e começam em `z = 0` (o ConstructCAD aplica a altura de montagem). Luminárias de teto ficam abaixo de `z = 0`. Vegetação fica com o tronco na origem e a base no chão (`z = 0`).
- **Paisagismo**: as fontes de `sources/planting/` saem de `tools/vegetation.py`; altere o gerador, não o JSON. Cada espécie é uma malha fixa no porte adulto, por isso é um componente próprio com um tipo (o ConstructCAD guarda uma definição por componente).
- **Parâmetros**: nomes em português, sem acentos nem espaços (`Largura`, `Profundidade`, `Altura`, `Elevacao`). Marque `instance: true` só no que muda por elemento (altura de instalação, queda de pendente).
- **Tipos**: um componente com vários tamanhos é melhor que vários componentes. O nome do tipo diz o tamanho (`Balcão 80 cm`).
- **Nomes únicos**: o componente e os tipos não podem repetir nomes do template do ConstructCAD; o build avisa.
- **MEP**: louças com `mep.Fixture` (UHC pela NBR 8160, peso pela NBR 5626, `hot_water`); dispositivos com `mep.Device` (`Outlet`, `DedicatedOutlet`, `Switch`, `CeilingLight`, `WallLight`, `Panel`) e a potência em VA. A potência e as UHC valem para todos os tipos do componente: potências diferentes pedem componentes diferentes.
- **Fabricantes**: componentes genéricos ficam com `manufacturer` vazio. Componentes de um fabricante real só com medidas públicas do catálogo dele, `manufacturer`, `model` e `url` preenchidos, e sem logotipos ou imagens dele.
- **Licença**: ao contribuir, você concorda em licenciar sua contribuição sob [CC BY 4.0](LICENSE) e declara que tem o direito de fazê-lo.

## Pull requests

O CI (`Validate`) gera os componentes a partir das fontes com o ConstructCAD fixado, carrega cada `.ccomp` num projeto novo e confere se o catálogo está atualizado. Um PR só entra com o CI verde.
