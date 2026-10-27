# Portas e janelas · Doors and windows

Ainda não há portas nem janelas nesta biblioteca, nem nesta pasta nem em [`windows`](../windows).

No ConstructCAD 0.5, portas e janelas são tipos nativos hospedados na parede (`TypeData::Door { width, height, material }` e `TypeData::Window { width, height, default_sill, material }`), e um `.ccomp` só guarda componentes (`TypeData::Component`). Um componente não abre vão na parede, então uma "porta" feita como componente não funcionaria como porta.

Caminhos possíveis no ConstructCAD:

- **Portas e janelas paramétricas como componentes hospedados**: um `ComponentKind::Door`/`Window` cuja definição traga a geometria (folhas, batentes, caixilhos) e o vão que abre na parede, salvo em `.ccomp` como os demais.
- **Arquivos de tipo para as categorias nativas**: estender o `.ccomp` (ou criar um formato irmão) para levar tipos de porta e janela com suas dimensões e materiais.

Quando um deles existir, os tipos de porta (giro, correr, camarão, pivotante; 60 a 90 cm × 210 cm) e de janela (correr, maxim-ar, basculante; peitoris usuais) entram aqui.

---

*Doors and windows are native wall-hosted types in ConstructCAD 0.5, and a `.ccomp` holds only components, which do not cut walls. They will be added here once ConstructCAD can save door and window types, or hosted door/window components, to a file.*
