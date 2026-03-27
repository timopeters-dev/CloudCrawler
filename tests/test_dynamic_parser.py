import asyncio
import sys
import os

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from parsers.dynamic_parser import DynamicParser

async def test_flat_parsing():
    html = "<html><body><h1>Title</h1><p>Description</p></body></html>"
    selectors = {"title": "h1", "desc": "p"}
    parser = DynamicParser()
    results = await parser.parse(html, selectors)
    print("Flat Parsing Results:", results)
    assert len(results) == 1
    assert results[0]["title"] == "Title"
    assert results[0]["desc"] == "Description"

async def test_table_parsing():
    html = """
    <table>
        <tr class="team"><td>Team A</td><td>10</td></tr>
        <tr class="team"><td>Team B</td><td>8</td></tr>
    </table>
    """
    row_selector = "tr.team"
    selectors = {"name": "td:nth-child(1)", "points": "td:nth-child(2)"}
    parser = DynamicParser()
    results = await parser.parse(html, selectors, row_selector)
    print("Table Parsing Results:", results)
    assert len(results) == 2
    assert results[0]["name"] == "Team A"
    assert results[1]["name"] == "Team B"

if __name__ == "__main__":
    asyncio.run(test_flat_parsing())
    asyncio.run(test_table_parsing())
    print("All tests passed!")
