from click.testing import CliRunner
from vireon.__main__ import cli

def test_info_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['info'])
    assert result.exit_code == 0
    assert "VIREON" in result.output

def test_validate_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['validate'])
    assert result.exit_code == 0

def test_run_command_basic():
    runner = CliRunner()
    result = runner.invoke(cli, ['run', '--duration', '0.1', '--board', 'synthetic'])
    assert result.exit_code == 0

def test_ctf_list_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['ctf', 'list'])
    assert result.exit_code == 0

def test_fuzz_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['fuzz', '--iterations', '1'])
    assert result.exit_code == 0

def test_stride_command(tmp_path):
    output_json = tmp_path / "model.json"
    output_md = tmp_path / "model.md"
    runner = CliRunner()
    result = runner.invoke(cli, ['stride', '-o', str(output_json), '-m', str(output_md)])
    assert result.exit_code == 0
    assert output_json.exists()
    assert output_md.exists()

def test_sbom_command(tmp_path):
    output_json = tmp_path / "sbom.json"
    runner = CliRunner()
    result = runner.invoke(cli, ['sbom', '-o', str(output_json)])
    assert result.exit_code == 0
    assert output_json.exists()

def test_compliance_report_command(tmp_path):
    output_json = tmp_path / "compliance.json"
    runner = CliRunner()
    result = runner.invoke(cli, ['compliance-report', '-o', str(output_json)])
    assert result.exit_code == 0
    assert output_json.exists()

def test_audit_spdf_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['audit-spdf'])
    assert result.exit_code == 0

def test_monitor_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['monitor'])
    assert result.exit_code == 0
