"""Export functionality for BioStat."""
import numpy as np
import pandas as pd
from datetime import datetime


def export_results_to_html(results_dict, title="Resultados BioStat"):
    """
    Export analysis results to HTML file.

    Args:
        results_dict: dict with analysis results
        title: report title

    Returns:
        HTML string
    """
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; color: #333; }}
        h1 {{ color: #2c3650; border-bottom: 2px solid #4f6ef7; padding-bottom: 10px; }}
        h2 {{ color: #4f6ef7; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4f6ef7; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .significant {{ color: #16a34a; font-weight: bold; }}
        .not-significant {{ color: #d97706; }}
        .footer {{ margin-top: 30px; padding-top: 10px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
"""
    for section, data in results_dict.items():
        html += f"<h2>{section}</h2>\n"
        if isinstance(data, dict):
            html += "<table>\n"
            html += "<tr><th>Estadística</th><th>Valor</th></tr>\n"
            for key, value in data.items():
                if isinstance(value, float):
                    value = f"{value:.6f}"
                html += f"<tr><td>{key}</td><td>{value}</td></tr>\n"
            html += "</table>\n"
        elif isinstance(data, list):
            html += "<table>\n"
            html += "<tr>" + "".join(f"<th>{col}</th>" for col in data[0].keys()) + "</tr>\n"
            for row in data:
                html += "<tr>" + "".join(f"<td>{v}</td>" for v in row.values()) + "</tr>\n"
            html += "</table>\n"

    html += """
    <div class="footer">
        <p>Generado por BioStat - Software estadístico para laboratorio clínico</p>
    </div>
</body>
</html>
"""
    return html


def export_data_to_csv(dataframe, filepath):
    """
    Export DataFrame to CSV file.

    Args:
        dataframe: pandas DataFrame
        filepath: output file path

    Returns:
        bool: True if successful
    """
    try:
        dataframe.to_csv(filepath, index=False, encoding='utf-8')
        return True
    except Exception as e:
        print(f"Error exporting to CSV: {e}")
        return False


def export_data_to_excel(dataframe, filepath):
    """
    Export DataFrame to Excel file.

    Args:
        dataframe: pandas DataFrame
        filepath: output file path

    Returns:
        bool: True if successful
    """
    try:
        dataframe.to_excel(filepath, index=False, engine='openpyxl')
        return True
    except Exception as e:
        print(f"Error exporting to Excel: {e}")
        return False


def create_summary_report(data, analyses_performed):
    """
    Create a summary report of all analyses performed.

    Args:
        data: pandas DataFrame with source data
        analyses_performed: list of (analysis_name, results) tuples

    Returns:
        dict with complete report
    """
    report = {
        'metadata': {
            'title': 'Informe Estadístico BioStat',
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'n_observations': len(data),
            'n_variables': len(data.columns),
            'variables': list(data.columns),
        },
        'descriptive_statistics': {},
        'analyses': []
    }

    for col in data.select_dtypes(include=[np.number]).columns:
        d = data[col].dropna()
        report['descriptive_statistics'][col] = {
            'n': len(d),
            'mean': float(d.mean()),
            'median': float(d.median()),
            'std': float(d.std()),
            'min': float(d.min()),
            'max': float(d.max()),
        }

    for analysis_name, results in analyses_performed:
        report['analyses'].append({
            'name': analysis_name,
            'results': results
        })

    return report


def format_p_value(p):
    """Format p-value for display."""
    if p < 0.001:
        return "< 0.001"
    elif p < 0.01:
        return f"{p:.4f}"
    else:
        return f"{p:.4f}"


def format_number(value, decimals=4):
    """Format number for display."""
    if isinstance(value, (int, np.integer)):
        return str(value)
    elif isinstance(value, float):
        return f"{value:.{decimals}f}"
    else:
        return str(value)
