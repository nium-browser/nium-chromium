// Nium — chrome://nium serves the Nium interface and exposes the native bridge.

#include "nium/browser/ui/webui/nium_ui.h"

#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "base/base_paths.h"
#include "base/command_line.h"
#include "base/files/file_path.h"
#include "base/files/file_util.h"
#include "base/functional/bind.h"
#include "base/memory/ref_counted_memory.h"
#include "base/path_service.h"
#include "base/strings/string_util.h"
#include "base/task/thread_pool.h"
#include "chrome/browser/profiles/profile.h"
#include "content/public/browser/web_ui.h"
#include "content/public/browser/web_ui_data_source.h"
#include "nium/browser/ui/webui/nium_handler.h"

namespace nium {

namespace {

std::vector<base::FilePath> UiDirs() {
  std::vector<base::FilePath> dirs;
  const base::CommandLine* command_line = base::CommandLine::ForCurrentProcess();
  if (command_line->HasSwitch(kNiumUiDirSwitch)) {
    dirs.push_back(command_line->GetSwitchValuePath(kNiumUiDirSwitch));
  }
  base::FilePath exe_dir;
  if (base::PathService::Get(base::DIR_EXE, &exe_dir)) {
    dirs.push_back(exe_dir.AppendASCII("nium_ui"));
    // src\out\<build>\chrome.exe -> src\nium\ui
    dirs.push_back(exe_dir.DirName().DirName().AppendASCII("nium").AppendASCII("ui"));
  }
  return dirs;
}

// Only plain relative paths inside the interface folder are served.
bool IsSafePath(const std::string& path) {
  if (path.empty() || path.size() > 260 || !base::IsStringASCII(path)) {
    return false;
  }
  if (path.front() == '/' || path.find("..") != std::string::npos ||
      path.find('\\') != std::string::npos || path.find(':') != std::string::npos) {
    return false;
  }
  return true;
}

scoped_refptr<base::RefCountedMemory> ReadUiFile(std::vector<base::FilePath> dirs,
                                                 std::string path) {
  for (const base::FilePath& dir : dirs) {
    std::string data;
    if (base::ReadFileToString(dir.AppendASCII(path), &data)) {
      return base::MakeRefCounted<base::RefCountedString>(std::move(data));
    }
  }
  if (path == "index.html") {
    std::string page =
        "<!doctype html><meta charset=utf-8><title>Nium</title>"
        "<body style=\"font:15px system-ui;margin:40px;color:#222\">"
        "<h2>Interface do Nium n&atilde;o encontrada</h2>"
        "<p>Procurei nestas pastas:</p><ul>";
    for (const base::FilePath& dir : dirs) {
      page += "<li><code>" + dir.AsUTF8Unsafe() + "</code></li>";
    }
    page += "</ul><p>Use <code>--nium-ui-dir=&lt;pasta&gt;</code> para indicar outra.</p>";
    return base::MakeRefCounted<base::RefCountedString>(std::move(page));
  }
  return nullptr;
}

void ServeUiFile(const std::string& request_path,
                 content::WebUIDataSource::GotDataCallback callback) {
  std::string path = request_path.substr(0, request_path.find_first_of("?#"));
  if (path.empty()) {
    path = "index.html";
  }
  if (!IsSafePath(path)) {
    std::move(callback).Run(nullptr);
    return;
  }
  base::ThreadPool::PostTaskAndReplyWithResult(
      FROM_HERE, {base::MayBlock(), base::TaskPriority::USER_BLOCKING},
      base::BindOnce(&ReadUiFile, UiDirs(), path), std::move(callback));
}

}  // namespace

NiumUI::NiumUI(content::WebUI* web_ui) : content::WebUIController(web_ui) {
  Profile* profile = Profile::FromWebUI(web_ui);
  content::WebUIDataSource* source =
      content::WebUIDataSource::CreateAndAdd(profile, kNiumHost);
  // The interface builds its markup with innerHTML (escaped), as in the Electron version.
  source->DisableTrustedTypesCSP();
  source->SetRequestFilter(
      base::BindRepeating([](const std::string&) { return true; }),
      base::BindRepeating(&ServeUiFile));
  web_ui->AddMessageHandler(
      std::make_unique<NiumHandler>(profile->GetPath().AppendASCII("Nium")));
}

NiumUI::~NiumUI() = default;

}  // namespace nium
