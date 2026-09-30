from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
CARPETA = BASE_DIR / "OTS_MAXIMO"


archivos = sorted(
    CARPETA.glob("*.xlsx")
)


if not archivos:
    print("No se encontraron archivos XLSX.")
    raise SystemExit


print("\nARCHIVOS ENCONTRADOS")
print("====================")

for archivo in archivos:
    print(f"- {archivo.name}")


todos = []


for archivo in archivos:

    df = pd.read_excel(
        archivo,
        engine="openpyxl"
    )

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # -----------------------------
    # DETECTAR COLUMNA DE OT
    # -----------------------------

    if "WORK ORDER" in df.columns:
        columna_ot = "WORK ORDER"

    elif "WONUM" in df.columns:
        columna_ot = "WONUM"

    else:
        print(
            f"\nERROR: {archivo.name} "
            f"no tiene WORK ORDER ni WONUM."
        )

        print(
            "Columnas encontradas:"
        )

        print(
            df.columns.tolist()
        )

        raise SystemExit


    df["_NUMERO_OT"] = (
        df[columna_ot]
        .astype(str)
        .str.strip()
        .str.upper()
    )


    # quitar valores vacíos
    df = df[
        ~df["_NUMERO_OT"].isin(
            [
                "",
                "NAN",
                "NONE",
                "NULL"
            ]
        )
    ].copy()


    df["_ARCHIVO"] = (
        archivo.name
    )


    todos.append(
        df[
            [
                "_NUMERO_OT",
                "_ARCHIVO"
            ]
        ]
    )


df_total = pd.concat(
    todos,
    ignore_index=True
)


total_filas = len(
    df_total
)

total_ots_unicas = (
    df_total[
        "_NUMERO_OT"
    ]
    .nunique()
)


duplicados = (
    df_total[
        df_total.duplicated(
            "_NUMERO_OT",
            keep=False
        )
    ]
    .sort_values(
        "_NUMERO_OT"
    )
)


print("\n")
print("==============================")
print("RESULTADO")
print("==============================")

print(
    f"Filas totales: {total_filas}"
)

print(
    f"OTs únicas: {total_ots_unicas}"
)

print(
    f"Registros duplicados: "
    f"{len(duplicados)}"
)


if duplicados.empty:

    print("\n✅ No hay OTs repetidas.")

    print(
        "La estructura UNIQUE(numero_ot) "
        "es compatible con tus archivos."
    )

else:

    print(
        "\n⚠️ Hay OTs repetidas."
    )

    print(
        "\nPrimeros duplicados:"
    )

    print(
        duplicados.head(50)
        .to_string(index=False)
    )
