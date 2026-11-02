// Nium — uma etapa da compilação. Cada etapa tem até 6 h (limite do GitHub): continua de onde a
// anterior parou, compila até o tempo acabar e salva o progresso para a próxima.
// Baseado na compilação do ungoogled-chromium-windows (BSD-3-Clause).
import * as core from '@actions/core';
import * as io from '@actions/io';
import * as exec from '@actions/exec';
import { DefaultArtifactClient } from '@actions/artifact';

const BUILD_TIMEOUT_EXIT_CODE = 124;
const STATE = 'nium-build-state';
const FINAL = 'nium-windows';
// A compilação para aos 300 min da etapa; sobra 1 h para salvar o progresso (zip + envio).
const BUILD_UNTIL_MINUTES = 300;

async function upload(artifact, name, files, root, retentionDays) {
  for (let i = 0; i < 5; ++i) {
    try { await artifact.deleteArtifact(name); } catch (e) { /* ainda não existe */ }
    try {
      await artifact.uploadArtifact(name, files, root, {retentionDays, compressionLevel: 0});
      return;
    } catch (e) {
      console.error(`Falha ao enviar ${name}: ${e}`);
      await new Promise(r => setTimeout(r, 10000));
    }
  }
  throw new Error(`Não foi possível enviar ${name}`);
}

async function run() {
  process.on('SIGINT', () => {});
  const finished = core.getBooleanInput('finished', {required: true});
  const fromArtifact = core.getBooleanInput('from_artifact', {required: true});
  if (finished) {
    core.setOutput('finished', true);
    return;
  }
  const artifact = new DefaultArtifactClient();

  if (fromArtifact) {
    await exec.exec(process.execPath, [`${import.meta.dirname}\\download.js`, STATE, 'C:\\nium']);
    await exec.exec('7z', ['x', 'C:\\nium\\state.zip', '-oC:\\nium', '-y', '-bso0', '-bsp0']);
    await io.rmRF('C:\\nium\\state.zip');
  }

  const started = Number(process.env.NIUM_JOB_START || Date.now() / 1000);
  const elapsed = (Date.now() / 1000 - started) / 60;
  const minutes = Math.max(0, BUILD_UNTIL_MINUTES - elapsed);
  const args = ['ci\\build.py', '--minutes', minutes.toFixed(0)];
  if (!fromArtifact) args.push('--fresh');
  const code = await exec.exec('python', args, {ignoreReturnCode: true});

  if (code === 0) {
    const zips = (await exec.getExecOutput('cmd', ['/c', 'dir /b C:\\nium\\dist\\*.zip'])).stdout
      .split(/\r?\n/).map(s => s.trim()).filter(Boolean).map(s => `C:\\nium\\dist\\${s}`);
    await upload(artifact, FINAL, zips, 'C:\\nium\\dist', 30);
    core.setOutput('finished', true);
  } else if (code === BUILD_TIMEOUT_EXIT_CODE) {
    await new Promise(r => setTimeout(r, 5000));
    await exec.exec('7z', ['a', '-tzip', 'C:\\nium\\state.zip', 'C:\\nium\\src', '-mx=3', '-mtc=on',
      '-mmt=on', '-bso0', '-bsp0'], {ignoreReturnCode: true});
    await upload(artifact, STATE, ['C:\\nium\\state.zip'], 'C:\\nium', 3);
    core.setOutput('finished', false);
  } else {
    throw new Error(`A compilação falhou (código ${code}). Veja o erro acima.`);
  }
}

run().catch(err => core.setFailed(err.message));
