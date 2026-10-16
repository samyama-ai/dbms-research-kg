"""Build and load the DBMS Research graph into Samyama."""
import click

@click.command()
@click.option("--limit", type=int, default=None, help="Cap rows per source for a fast demo load.")
def main(limit):
    # TODO: connect -> run schema/dbms_research_kg.cypher -> load nodes/edges
    print(f"[loader] loading dbms_research KG (limit={limit}) ...")

if __name__ == "__main__":
    main()
