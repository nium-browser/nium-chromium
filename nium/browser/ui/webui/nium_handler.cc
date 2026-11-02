// Nium — the native side of window.nium: chrome.send('nium.call', [id, method, params]).
// Each call is answered with cr.webUIResponse(id, ok, value).

#include "nium/browser/ui/webui/nium_handler.h"

#include <optional>
#include <string>
#include <utility>

#include "base/files/file_util.h"
#include "base/functional/bind.h"
#include "base/json/json_reader.h"
#include "base/json/json_writer.h"
#include "base/task/thread_pool.h"
#include "components/version_info/version_info.h"
#include "content/public/browser/page_navigator.h"
#include "content/public/browser/web_contents.h"
#include "content/public/browser/web_ui.h"
#include "content/public/common/referrer.h"
#include "content/public/common/url_constants.h"
#include "ui/base/page_transition_types.h"
#include "ui/base/window_open_disposition.h"
#include "url/gurl.h"

namespace nium {

namespace {

constexpr char kNiumVersion[] = "0.3.0";
constexpr size_t kMaxStoreBytes = 8 * 1024 * 1024;

// Store keys become file names: letters, digits, '-' and '_' only.
bool IsValidKey(const std::string& key) {
  if (key.empty() || key.size() > 64) {
    return false;
  }
  for (char c : key) {
    if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
          (c >= '0' && c <= '9') || c == '-' || c == '_')) {
      return false;
    }
  }
  return true;
}

base::Value ReadStore(base::FilePath file) {
  std::string text;
  if (!base::ReadFileToStringWithMaxSize(file, &text, kMaxStoreBytes)) {
    return base::Value();
  }
  std::optional<base::Value> value =
      base::JSONReader::Read(text, base::JSON_PARSE_RFC);
  return value ? std::move(*value) : base::Value();
}

bool WriteStore(base::FilePath file, std::string json) {
  if (!base::CreateDirectory(file.DirName())) {
    return false;
  }
  base::FilePath temp = file.AddExtensionASCII("tmp");
  return base::WriteFile(temp, json) && base::ReplaceFile(temp, file, nullptr);
}

}  // namespace

NiumHandler::NiumHandler(base::FilePath store_dir)
    : store_dir_(std::move(store_dir)) {}

NiumHandler::~NiumHandler() {
  StopWatchingTabs();
}

void NiumHandler::RegisterMessages() {
  web_ui()->RegisterMessageCallback(
      "nium.call", base::BindRepeating(&NiumHandler::HandleCall,
                                       base::Unretained(this)));
}

void NiumHandler::HandleCall(const base::ListValue& args) {
  AllowJavascript();
  if (args.size() < 2 || !args[0].is_string() || !args[1].is_string()) {
    return;
  }
  base::Value id = args[0].Clone();
  const std::string method = args[1].GetString();
  const base::DictValue* params =
      args.size() > 2 ? args[2].GetIfDict() : nullptr;

  if (method == "version") {
    base::DictValue info;
    info.Set("nium", kNiumVersion);
    info.Set("chromium", std::string(version_info::GetVersionNumber()));
    Reply(std::move(id), true, base::Value(std::move(info)));
    return;
  }

  if (method.starts_with("tabs.")) {
    if (!HandleTabsCall(id, method, params)) {
      Reply(std::move(id), false, base::Value("Função desconhecida: " + method));
    }
    return;
  }

  if (method == "openTab") {
    const std::string* raw = params ? params->FindString("url") : nullptr;
    GURL url(raw ? *raw : std::string());
    if (!url.is_valid() ||
        !(url.SchemeIsHTTPOrHTTPS() || url.SchemeIs(content::kChromeUIScheme))) {
      Reply(std::move(id), false, base::Value("Endereço inválido."));
      return;
    }
    web_ui()->GetWebContents()->OpenURL(
        content::OpenURLParams(url, content::Referrer(),
                               WindowOpenDisposition::kNewForegroundTab,
                               ui::PAGE_TRANSITION_AUTO_TOPLEVEL,
                               /*is_renderer_initiated=*/false),
        {});
    Reply(std::move(id), true, base::Value(true));
    return;
  }

  if (method == "storeGet" || method == "storeSet") {
    const std::string* key = params ? params->FindString("key") : nullptr;
    if (!key || !IsValidKey(*key)) {
      Reply(std::move(id), false, base::Value("Chave inválida."));
      return;
    }
    base::FilePath file = store_dir_.AppendASCII(*key + ".json");
    if (method == "storeGet") {
      base::ThreadPool::PostTaskAndReplyWithResult(
          FROM_HERE, {base::MayBlock(), base::TaskPriority::USER_VISIBLE},
          base::BindOnce(&ReadStore, file),
          base::BindOnce(&NiumHandler::ReplyValue,
                         weak_factory_.GetWeakPtr(), std::move(id)));
      return;
    }
    const base::Value* value = params->Find("value");
    std::optional<std::string> json =
        value ? base::WriteJson(*value) : std::nullopt;
    if (!json || json->size() > kMaxStoreBytes) {
      Reply(std::move(id), false, base::Value("Valor inválido."));
      return;
    }
    base::ThreadPool::PostTaskAndReplyWithResult(
        FROM_HERE, {base::MayBlock(), base::TaskPriority::USER_VISIBLE},
        base::BindOnce(&WriteStore, file, std::move(*json)),
        base::BindOnce(&NiumHandler::ReplyBool, weak_factory_.GetWeakPtr(),
                       std::move(id)));
    return;
  }

  Reply(std::move(id), false, base::Value("Função desconhecida: " + method));
}

TabsBridge* NiumHandler::Tabs() {
  if (!tabs_) {
    if (TabsBridge* bridge =
            TabsBridge::FromWebContents(web_ui()->GetWebContents())) {
      tabs_ = bridge->GetWeakPtr();
    }
  }
  return tabs_.get();
}

bool NiumHandler::HandleTabsCall(base::Value& id,
                                 const std::string& method,
                                 const base::DictValue* params) {
  TabsBridge* tabs = Tabs();
  if (!tabs) {
    Reply(std::move(id), false,
          base::Value("Esta página não está na barra lateral de uma janela."));
    return true;
  }
  const std::optional<int> tab_id =
      params ? params->FindInt("id") : std::nullopt;

  if (method == "tabs.list") {
    Reply(std::move(id), true, base::Value(tabs->ListTabs()));
  } else if (method == "tabs.watch") {
    // From now on the page gets the "nium-tabs" event with the full list on every change.
    if (!watching_tabs_) {
      tabs->SetListener(this);
      watching_tabs_ = true;
    }
    Reply(std::move(id), true, base::Value(tabs->ListTabs()));
  } else if (method == "tabs.new") {
    tabs->NewTab();
    Reply(std::move(id), true, base::Value(true));
  } else if (method == "tabs.activate" || method == "tabs.close") {
    const bool ok = tab_id && (method == "tabs.activate"
                                   ? tabs->ActivateTab(*tab_id)
                                   : tabs->CloseTab(*tab_id));
    Reply(std::move(id), ok,
          ok ? base::Value(true) : base::Value("Aba não encontrada."));
  } else if (method == "tabs.move") {
    const std::optional<int> index =
        params ? params->FindInt("index") : std::nullopt;
    const bool ok = tab_id && index && tabs->MoveTab(*tab_id, *index);
    Reply(std::move(id), ok,
          ok ? base::Value(true) : base::Value("Aba não encontrada."));
  } else {
    return false;
  }
  return true;
}

void NiumHandler::OnTabsChanged() {
  TabsBridge* tabs = tabs_.get();
  if (!tabs || !IsJavascriptAllowed()) {
    return;
  }
  FireWebUIListener("nium-tabs", base::Value(tabs->ListTabs()));
}

void NiumHandler::StopWatchingTabs() {
  if (watching_tabs_ && tabs_) {
    tabs_->SetListener(nullptr);
  }
  watching_tabs_ = false;
}

void NiumHandler::OnJavascriptDisallowed() {
  // The page reloaded or went away: stop pushing tab updates and drop pending replies.
  StopWatchingTabs();
  weak_factory_.InvalidateWeakPtrs();
}

void NiumHandler::ReplyValue(base::Value callback_id, base::Value result) {
  Reply(std::move(callback_id), true, std::move(result));
}

void NiumHandler::ReplyBool(base::Value callback_id, bool ok) {
  if (ok) {
    Reply(std::move(callback_id), true, base::Value(true));
  } else {
    Reply(std::move(callback_id), false,
          base::Value("Não foi possível salvar."));
  }
}

void NiumHandler::Reply(base::Value callback_id, bool ok, base::Value result) {
  if (!IsJavascriptAllowed()) {
    return;
  }
  if (ok) {
    ResolveJavascriptCallback(callback_id, result);
  } else {
    RejectJavascriptCallback(callback_id, result);
  }
}

}  // namespace nium
