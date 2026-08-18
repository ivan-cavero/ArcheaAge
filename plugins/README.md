# Plugins

Catálogo de plugins comunitarios para ArcheaAge. Cada plugin:

1. Referencia `ArcheaAge.Sdk` (NuGet) — no clona el server.
2. Implementa `IAaPlugin` (Id, Name, Version, OnLoad/OnUnload).
3. Se suscribe a eventos del bus (`PlayerLoggedIn`, `QuestCompleted`, `ItemCrafted`, ...).
4. Trae sus propios tests (el CI los ejecuta contra cada release del SDK — matriz de compatibilidad).

## Reglas de entrada al catálogo

- Código open source (LGPLv3 o compatible).
- Build verde + tests en CI.
- Sin acceso a datos de jugadores fuera del contrato del SDK.
- Los cambios que tocan el client (zonas, modelos, UI) van como **content packs** en `../content/`, no en el plugin.

## Example

```bash
dotnet build plugins/Example
```

Referencia de estructura: `Example/ExamplePlugin.cs`.
