# Lovable prompt: every refusal, advisory and crash page in the reader's language (item 130)

> **NOT APPLIED** (see PROMPT-STATUS.md). Backend gate: every error body now
> carries `code` beside the unchanged English `error`, the setup advisories
> carry `code` + their numbers, and the statement advisories carry a parallel
> `*_detail`. Paste after that backend is deployed (`docs/api-contract.md`,
> "Error codes"). Until then every string below simply never matches and the
> app renders exactly as today.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Do not change any request the app makes: this is a rendering change only. Auth stays the existing `Authorization: Bearer <token>`. Render defensively everywhere: a response WITHOUT the new fields must render exactly as it does today.

## Why

When the tool refuses something, the toast is the backend's English sentence, verbatim, on a screen Criss reads in Portuguese. The dictionary has 1,400 keys in both languages and none of them is this: `toast.error(e.message)` at ~40 sites, the two amber advisory boxes at the top of a month, the "amount mismatch" chip, and the crash page. The backend now sends a stable `code` beside the English sentence, plus the values the sentence names (a file, a month, a card, a count), so the app can say it in the reader's language and fall back to the English sentence for any code it does not know.

## 1. `src/lib/api.ts`: carry the code on the error

`ApiError` gains two fields, both optional:

```ts
export class ApiError extends Error {
  status: number;
  data: unknown;
  code?: string;
  fields?: Record<string, unknown>;
  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.status = status;
    this.data = data;
    const d = (data ?? {}) as Record<string, unknown>;
    if (typeof d.code === "string") this.code = d.code;
    if (d && typeof d === "object") {
      const { error: _e, code: _c, detail: _d, ...rest } = d;
      this.fields = rest;                 // file, month, card, limit, ...
    }
  }
}
```

- In `apiFetch`, the `!res.ok` branch already parses the body into `data` and passes it to `ApiError`; nothing else changes there. The message stays `String(d.error)` so an unknown code still reads.
- The 401 branch throws `new ApiError(401, "Unauthorized")` without reading a body. Read it the same way as the others (`try { data = await res.json() } catch {}`) and pass it, so the login screen can use `unauthenticated` / `invalid_login_code`. Keep clearing the token and emitting unauthorized exactly as today.
- `downloadFile` builds its own `ApiError`: pass the parsed body as `data` there too (`throw new ApiError(res.status, msg, data)`), so a download refusal (`run_not_found`, `statement_not_workbook`) localizes like any other.

## 2. `src/lib/errorText.ts` (new): one place that turns an error into a sentence

```ts
import { ApiError } from "@/lib/api";
import { hasKey, type TKey } from "@/lib/i18n";

type T = (key: TKey, vars?: Record<string, string | number>) => string;

/** The refusal in the reader's language: the backend's stable `code` when the
 *  dictionary knows it, the backend's English sentence when it does not. */
export function errorText(e: unknown, t: T): string {
  if (e instanceof ApiError) {
    const key = `err.${e.code ?? ""}`;
    if (e.code && hasKey(key)) {
      const vars: Record<string, string | number> = {};
      for (const [k, v] of Object.entries(e.fields ?? {})) {
        vars[k] = Array.isArray(v) ? v.join(", ")
          : v == null ? ""
          : typeof v === "object" ? String((v as { label?: string; key?: string }).label
              ?? (v as { key?: string }).key ?? "")
          : String(v);
      }
      return t(key as TKey, vars);
    }
    return e.message;
  }
  return e instanceof Error ? e.message : String(e);
}
```

Nothing else in the app composes refusal text.

## 3. Use it wherever a refusal is shown

Replace the message with `errorText(e, t)` at every site that shows a caught error to the reader. `t` comes from the `useT()` the component already has (add `const t = useT();` where a component has none):

- `src/components/ExpensesReviewGrid.tsx`: every `onError: (e: Error) => toast.error(e.message)` and the two `toast.error((e as Error).message)`, the `setFieldErrors` line (`[vars.field]: errorText(e, t)`), the `setPhase({ kind: "error", msg: ... })` pairs, and the load-error block that renders `error.message`.
- `src/components/RunWorkbench.tsx`: the same `toast.error` / `setError` / load-error sites.
- `src/components/SettingsScreen.tsx`, `MemoryScreen.tsx`, `InboundLogScreen.tsx`, `TripsScreen.tsx`, `MonthsHome.tsx`, `OperatorDashboard.tsx`, `IntakePrepare.tsx`, `NewExpenseBatch.tsx`, `ReceiptsDropScreen.tsx`, `ReceiptsFolderUploader.tsx`, `StatementPanels.tsx`, `SummaryBar.tsx`, `CompareScreen.tsx`, `CostCentersScreen.tsx`, `FeedbackWidget.tsx`: same treatment at each `.message` shown to the reader.
- `src/components/LoginScreen.tsx`: keep the existing `login.wrongCode` / `login.generic` behaviour, but prefer `errorText` when the error carries a code (`invalid_login_code` and `too_many_login_attempts` both have keys below).

Do NOT touch `src/lib/error-capture.ts` or `lovable-error-reporting.ts`: those report to the server and must keep the raw English.

## 4. The advisories: render from the code, not the sentence

`summary.setup_advisories[]` entries now carry `code` plus the values the sentence used, beside the unchanged `message`. In `RunWorkbench.tsx`, the amber "This run is missing setup" list renders, per entry:

```tsx
const key = `adv.${a.code ?? ""}`;
<li>{a.code && hasKey(key) ? t(key as TKey, { ...a }) : a.message}</li>
```

Type: `{ setting: string; message: string; code?: string; [k: string]: unknown }`. The "Open Settings" button keeps keying off `a.setting === "cards"` exactly as today.

The second amber box renders `summary.statement_advisory`. It now has a parallel `summary.statement_advisory_detail` (`{code, ...values}` or null): when it is present and its code is known, render `t(\`adv.${detail.code}\`, detail)`, else the English `statement_advisory`. Same for the per-statement line in `StatementPanels.tsx`: `statements[].advisory_detail` beside `statements[].advisory`.

Month health is already localized (`wb.health.*` off `reason` / `suspects`); leave it alone.

## 5. The row chips are dictionary entries too

`getRowWarnings` in `RunWorkbench.tsx` builds English literals ("amount mismatch", "date mismatch", "near miss", "currency unknown") and `WarningChip` prints them. Return KEYS from `getRowWarnings` and translate in `WarningChip` (`title={warnings.map(t).join(", ")}`, body `t(warnings[0])`), so both the chip and its tooltip read in the reader's language. Keys: `warn.amountMismatch`, `warn.dateMismatch`, `warn.nearMiss`, `warn.currencyUnknown`. A warning string that comes from the API (`row.warnings`, `candidate.warnings`) is not a key: pass it through unchanged (`hasKey(w) ? t(w) : w`).

## 6. The crash page

`src/lib/error-page.ts` renders one English page from the server. Keep the markup, add the Portuguese text and pick between them in the page itself, from the same key the app stores its language under (`localStorage["brisken.lang"]`, values `"en"` / `"pt"`):

```html
<h1 data-en="This page didn't load" data-pt="Esta página não carregou"></h1>
<p data-en="Something went wrong on our end. You can try refreshing or head back home."
   data-pt="Algo deu errado do nosso lado. Você pode atualizar a página ou voltar ao início."></p>
<button class="primary" data-en="Try again" data-pt="Tentar de novo" onclick="location.reload()"></button>
<a class="secondary" href="/" data-en="Go home" data-pt="Voltar ao início"></a>
<script>
  (function () {
    var lang = "en";
    try { lang = localStorage.getItem("brisken.lang") === "pt" ? "pt" : "en"; } catch (e) {}
    document.documentElement.lang = lang === "pt" ? "pt-BR" : "en";
    document.querySelectorAll("[data-en]").forEach(function (el) {
      el.textContent = el.getAttribute("data-" + lang) || el.getAttribute("data-en");
    });
    document.title = lang === "pt" ? "Esta página não carregou" : "This page didn't load";
  })();
</script>
```

The `<title>` stays English in the markup and is swapped by the script, so a page rendered before the script runs is never blank.

## New strings

Every key below goes in BOTH dictionaries in `src/lib/i18n.tsx`. `{...}` placeholders are the fields the backend sends beside the code; a placeholder the backend did not send renders empty, which every sentence here survives.

### Refusals (`err.*`)

| Key | EN | PT-BR |
|---|---|---|
| `err.unauthenticated` | Your session has ended. Log in again. | Sua sessão terminou. Entre novamente. |
| `err.invalid_login_code` | That access code is not right. | Esse código de acesso não está correto. |
| `err.too_many_login_attempts` | Too many attempts. Wait a moment and try again. | Muitas tentativas. Espere um momento e tente de novo. |
| `err.not_found` | This page is not available. | Esta página não está disponível. |
| `err.method_not_allowed` | This page is not available. | Esta página não está disponível. |
| `err.validation_failed` | The app sent something the server could not read. Reload the page and try again. | O aplicativo enviou algo que o servidor não conseguiu ler. Recarregue a página e tente de novo. |
| `err.invalid_json` | The app sent something the server could not read. Reload the page and try again. | O aplicativo enviou algo que o servidor não conseguiu ler. Recarregue a página e tente de novo. |
| `err.invalid_body` | The app sent something the server could not read. Reload the page and try again. | O aplicativo enviou algo que o servidor não conseguiu ler. Recarregue a página e tente de novo. |
| `err.request_refused` | The tool refused that. Nothing was changed. | A ferramenta recusou essa ação. Nada foi alterado. |
| `err.run_not_found` | This month no longer exists. | Este mês não existe mais. |
| `err.upload_not_found` | This upload no longer exists. | Este envio não existe mais. |
| `err.job_not_found` | This task no longer exists. | Esta tarefa não existe mais. |
| `err.not_an_expense_batch` | This is not a month of receipts. | Isto não é um mês de recibos. |
| `err.batch_deleted` | This month was deleted while you were working on it. Nothing was changed. | Este mês foi excluído enquanto você trabalhava nele. Nada foi alterado. |
| `err.label_required` | Give the month a name. | Dê um nome ao mês. |
| `err.delete_confirm_required` | To delete, type the month's name again. | Para excluir, digite o nome do mês novamente. |
| `err.delete_confirm_mismatch` | That name does not match this month. Nothing was deleted. | Esse nome não confere com este mês. Nada foi excluído. |
| `err.not_a_month` | Only a month can be published. | Somente um mês pode ser publicado. |
| `err.no_statement` | This month has no statement yet, so nothing is reconciled. Attach the statement, or publish anyway. | Este mês ainda não tem extrato, então nada foi conciliado. Anexe o extrato ou publique mesmo assim. |
| `err.month_not_complete` | This month is not finished yet. Publish anyway only if you mean to. | Este mês ainda não está concluído. Publique mesmo assim apenas se for essa a intenção. |
| `err.invalid_month` | Write the month as YYYY-MM, for example 2026-07. | Escreva o mês como AAAA-MM, por exemplo 2026-07. |
| `err.auto_materialize_off` | Creating months from waiting e-mail is switched off. | A criação de meses a partir dos e-mails em espera está desligada. |
| `err.no_statement_file` | Choose the statement file. | Escolha o arquivo do extrato. |
| `err.no_receipts_file` | Choose the receipts file. | Escolha o arquivo de recibos. |
| `err.no_replacement_file` | Choose at least one file to replace. | Escolha pelo menos um arquivo para substituir. |
| `err.intake_already_processing` | These files are already being processed, so they cannot be swapped. Send a new upload instead. | Estes arquivos já estão sendo processados, então não podem ser trocados. Envie um novo upload. |
| `err.intake_missing_receipts` | This upload has no receipts file yet. | Este envio ainda não tem arquivo de recibos. |
| `err.unsupported_statement_file` | The statement has to be a .csv, .xlsx or .pdf from the bank (this one is {suffix}). | O extrato precisa ser um .csv, .xlsx ou .pdf do banco (este é {suffix}). |
| `err.unsupported_receipts_file` | The receipts file has to be a .csv export or a Zoho Expense report .pdf. | O arquivo de recibos precisa ser um .csv exportado ou um relatório .pdf do Zoho Expense. |
| `err.receipts_source_needs_pdf` | "Zoho Expense report PDF" needs a .pdf file (this one is {suffix}). | "Relatório PDF do Zoho Expense" precisa de um arquivo .pdf (este é {suffix}). |
| `err.statement_columns_missing` | The tool could not find these columns in the statement: {missing}. Point them at the file's own headers and try again. | A ferramenta não encontrou estas colunas no extrato: {missing}. Indique as colunas do próprio arquivo e tente de novo. |
| `err.statement_unreadable` | The tool could not read this statement file. | A ferramenta não conseguiu ler este arquivo de extrato. |
| `err.statement_read_nothing` | {file} was read and held no charge at all, so nothing was added. The usual causes are the wrong worksheet, a header row that is not the first row, or a date format the tool does not read. | {file} foi lido e não continha nenhum lançamento, então nada foi adicionado. As causas mais comuns são a planilha errada, um cabeçalho que não está na primeira linha ou um formato de data que a ferramenta não lê. |
| `err.statement_on_trip` | Statements belong to a month, not to a trip. | Extratos pertencem a um mês, não a uma viagem. |
| `err.no_statement_to_reread` | This month has no statement to read again. | Este mês não tem extrato para reler. |
| `err.statement_file_missing` | The statement file {file} is no longer in this month's folder. Nothing was changed. | O arquivo de extrato {file} não está mais na pasta deste mês. Nada foi alterado. |
| `err.statement_reads_nothing_now` | {file} held {n_rows} charges when it was uploaded and now reads none. Nothing was changed. | {file} tinha {n_rows} lançamentos quando foi enviado e agora não traz nenhum. Nada foi alterado. |
| `err.reread_strands_decisions` | {n_decisions} decisions you already made sit on charges this re-read would drop. Nothing was changed. | {n_decisions} decisões que você já tomou estão em lançamentos que esta releitura descartaria. Nada foi alterado. |
| `err.concurrent_statement_upload` | Another statement landed on this month while this was running. Nothing was written, so nothing was lost. Try again. | Outro extrato chegou a este mês enquanto isto era processado. Nada foi gravado, então nada foi perdido. Tente de novo. |
| `err.statement_not_workbook` | This month's statement is not an Excel file, so there is nothing to download here. | O extrato deste mês não é um arquivo do Excel, então não há o que baixar aqui. |
| `err.pipeline_config_invalid` | The tool is not set up to read this month. Contact support. | A ferramenta não está configurada para ler este mês. Fale com o suporte. |
| `err.no_files_uploaded` | Choose at least one file. | Escolha pelo menos um arquivo. |
| `err.all_files_empty` | Every file you sent was empty. | Todos os arquivos enviados estavam vazios. |
| `err.no_receipt_files` | A trip needs at least one receipt. | Uma viagem precisa de pelo menos um recibo. |
| `err.no_readable_receipt_files` | None of those files could be read as a receipt. | Nenhum desses arquivos pôde ser lido como recibo. |
| `err.file_required` | Choose a file. | Escolha um arquivo. |
| `err.file_name_required` | Choose a file. | Escolha um arquivo. |
| `err.unsupported_attachment_type` | A receipt has to be a PDF or an image ({suffix} does not work). | Um recibo precisa ser PDF ou imagem ({suffix} não funciona). |
| `err.empty_file` | That file is empty. | Esse arquivo está vazio. |
| `err.file_too_large` | That file is larger than {limit_mb} MB. | Esse arquivo é maior que {limit_mb} MB. |
| `err.receipts_not_at_month_creation` | Receipts are added on the Receipts page, not when the month is created. Each one goes to the month printed on it. | Os recibos são adicionados na página Recibos, não na criação do mês. Cada um vai para o mês que está impresso nele. |
| `err.receipt_image_not_found` | There is no image for this receipt. | Não há imagem para este recibo. |
| `err.report_file_missing` | The file this receipt came from is no longer here. | O arquivo de onde este recibo veio não está mais aqui. |
| `err.expense_not_found` | This expense is no longer in this month. | Esta despesa não está mais neste mês. |
| `err.expense_already_removed` | This expense was already removed from this month. | Esta despesa já foi removida deste mês. |
| `err.expense_already_in_month` | This expense is already in {month}. | Esta despesa já está em {month}. |
| `err.month_move_not_needed` | This receipt's date is inside this month. Choose a month if you want to move it anyway. | A data deste recibo está dentro deste mês. Escolha um mês se quiser movê-lo mesmo assim. |
| `err.month_could_not_open` | The month {month} could not be opened. | Não foi possível abrir o mês {month}. |
| `err.trip_not_by_month` | A trip covers several months, so its receipts are not filed by month. | Uma viagem cobre vários meses, então seus recibos não são organizados por mês. |
| `err.file_missing_on_disk` | {file} is no longer stored. Send it again. | {file} não está mais armazenado. Envie de novo. |
| `err.set_aside_file_not_found` | {file} is not in this month's set-aside list. | {file} não está na lista de arquivos separados deste mês. |
| `err.set_aside_already_restored` | {file} was already brought back. | {file} já foi recuperado. |
| `err.set_aside_already_expense` | {file} is already an expense in this month. | {file} já é uma despesa deste mês. |
| `err.vendor_and_total_required` | An expense needs a supplier and an amount. | Uma despesa precisa de fornecedor e valor. |
| `err.unknown_field` | This field cannot be edited. | Este campo não pode ser editado. |
| `err.invalid_date` | Write the date as YYYY-MM-DD, for example 2026-07-31. | Escreva a data como AAAA-MM-DD, por exemplo 2026-07-31. |
| `err.invalid_number` | {field} has to be a number. | {field} precisa ser um número. |
| `err.invalid_currency` | The currency is a three-letter code, for example USD. | A moeda é um código de três letras, por exemplo USD. |
| `err.invalid_private_value` | That value is not valid here. | Esse valor não é válido aqui. |
| `err.legal_entity_required` | Choose the company. | Escolha a empresa. |
| `err.date_range_reversed` | The start date {from} is after the end date {to}. | A data inicial {from} é posterior à data final {to}. |
| `err.settled_outside_how_required` | Say how it was paid: {allowed}. | Informe como foi pago: {allowed}. |
| `err.receipt_not_in_month` | This receipt is not in this month. | Este recibo não está neste mês. |
| `err.receipt_settled_by_charge` | A charge on the statement already settles this receipt. Reject that match first. | Um lançamento do extrato já quita este recibo. Rejeite essa correspondência primeiro. |
| `err.invalid_decision_status` | That decision is not one the tool knows. | Essa decisão não é conhecida pela ferramenta. |
| `err.transaction_ids_required` | Choose at least one charge. | Escolha pelo menos um lançamento. |
| `err.too_many_rows` | At most {limit} rows at a time. | No máximo {limit} linhas por vez. |
| `err.transaction_not_found` | This charge is no longer in this month. | Este lançamento não está mais neste mês. |
| `err.receipt_not_found` | This receipt is no longer in this month. | Este recibo não está mais neste mês. |
| `err.entity_differs` | The receipt and the charge belong to different companies. | O recibo e o lançamento pertencem a empresas diferentes. |
| `err.receipt_settled_elsewhere` | This receipt already settles a charge in {batch}. A receipt can only settle one charge: reject it there first, or choose another receipt. | Este recibo já quita um lançamento em {batch}. Um recibo só pode quitar um lançamento: rejeite lá primeiro ou escolha outro recibo. |
| `err.receipt_just_settled` | Another month just claimed this receipt. Reload the page. | Outro mês acabou de reivindicar este recibo. Recarregue a página. |
| `err.company_card` | This expense was paid with the company card {card}, so there is nothing to reimburse. If someone paid with their own card, correct the card first. | Esta despesa foi paga com o cartão da empresa {card}, então não há nada a reembolsar. Se alguém pagou com o próprio cartão, corrija o cartão primeiro. |
| `err.private_card` | This expense is marked as paid with a private card. Undo that first if a company card paid. | Esta despesa está marcada como paga com cartão pessoal. Desfaça isso primeiro se quem pagou foi um cartão da empresa. |
| `err.reimburse_to_required` | Say who gets reimbursed. | Informe quem será reembolsado. |
| `err.category_not_allowed` | Choose one of the tool's categories. | Escolha uma das categorias da ferramenta. |
| `err.category_not_a_guess` | This category is not a guess to keep. Choose a category instead, or check the account. | Esta categoria não é um palpite a confirmar. Escolha uma categoria ou verifique a conta. |
| `err.cost_center_not_defined` | {cost_center} is not a defined cost center. Add it in Settings first. | {cost_center} não é um centro de custo cadastrado. Cadastre-o em Configurações primeiro. |
| `err.card_required` | Choose which card this statement is from. | Escolha de qual cartão é este extrato. |
| `err.card_not_defined` | The card {card} is not defined. Add it in Settings, Cards first. | O cartão {card} não está cadastrado. Cadastre-o em Configurações, Cartões primeiro. |
| `err.card_inactive` | The card {card} is inactive. Reactivate it before using it. | O cartão {card} está inativo. Reative-o antes de usá-lo. |
| `err.card_already_exists` | The card {card} already exists. Edit it in Settings, Cards. | O cartão {card} já existe. Edite-o em Configurações, Cartões. |
| `err.card_digits_invalid` | A card's digits are {min_digits} to {max_digits} numbers ({value} is not). | Os dígitos de um cartão têm de {min_digits} a {max_digits} números ({value} não tem). |
| `err.card_alias_generic` | "{alias}" names a kind of payment, not one card, so it would match every receipt paid that way. | "{alias}" indica um tipo de pagamento, não um cartão específico, então corresponderia a todos os recibos pagos assim. |
| `err.card_definition_invalid` | That card could not be saved. | Não foi possível salvar esse cartão. |
| `err.assignment_incomplete` | Each line needs a spelling and a card. | Cada linha precisa de uma grafia e de um cartão. |
| `err.hint_assigned_twice` | "{hint}" is assigned to two cards. Choose one. | "{hint}" está atribuído a dois cartões. Escolha um. |
| `err.hint_not_in_batch` | "{hint}" does not appear on any receipt in this month. | "{hint}" não aparece em nenhum recibo deste mês. |
| `err.nothing_to_apply` | There is nothing to save here. | Não há nada para salvar aqui. |
| `err.unknown_settings_keys` | These settings are not ones the server saves: {keys}. | Estas configurações não são salvas pelo servidor: {keys}. |
| `err.fx_rate_key_invalid` | A rate is written as FROM:TO, for example BRL:USD. | Uma taxa é escrita como DE:PARA, por exemplo BRL:USD. |
| `err.fx_rate_not_positive` | The rate {rate_key} has to be a number above zero. | A taxa {rate_key} precisa ser um número maior que zero. |
| `err.merchant_alias_generic` | "{alias}" is a generic word, so it would match unrelated suppliers. Use a word from {merchant}'s own name. | "{alias}" é uma palavra genérica e corresponderia a fornecedores sem relação. Use uma palavra do próprio nome de {merchant}. |
| `err.merchant_category_invalid` | {category} is not one of the tool's categories. | {category} não é uma das categorias da ferramenta. |
| `err.cost_center_case_duplicate` | {cost_center} and {other} differ only in capitals. Keep one. | {cost_center} e {other} diferem apenas em maiúsculas. Mantenha apenas um. |
| `err.cost_center_kind_invalid` | Choose a kind for {cost_center}: {allowed}. | Escolha um tipo para {cost_center}: {allowed}. |
| `err.trip_not_found` | This trip no longer exists. | Esta viagem não existe mais. |
| `err.trip_name_required` | Give the trip a name. | Dê um nome à viagem. |
| `err.trip_dates_invalid` | Write the dates as YYYY-MM-DD. | Escreva as datas como AAAA-MM-DD. |
| `err.trip_dates_reversed` | The trip cannot end before it starts. | A viagem não pode terminar antes de começar. |
| `err.travelers_invalid` | The travellers are a list of names. | Os viajantes são uma lista de nomes. |
| `err.too_many_travelers` | At most {limit} travellers. | No máximo {limit} viajantes. |
| `err.trip_id_required` | Choose the trip. | Escolha a viagem. |
| `err.trip_id_not_allowed` | Only a trip has a trip to choose. | Somente uma viagem tem uma viagem a escolher. |
| `err.invalid_batch_type` | That kind of month is not one the tool knows. | Esse tipo de mês não é conhecido pela ferramenta. |
| `err.trip_batch_being_created` | This trip's receipts are being created right now. Try again when that upload finishes. | Os recibos desta viagem estão sendo criados agora. Tente de novo quando o envio terminar. |
| `err.trip_batch_exists` | This trip already has its receipts. Add new ones to it instead. | Esta viagem já tem seus recibos. Adicione os novos a ela. |
| `err.trip_has_batch` | This trip still holds receipts. Delete those first. | Esta viagem ainda contém recibos. Exclua-os primeiro. |
| `err.receipt_column_map_invalid` | The receipt column settings are not valid. | As configurações de colunas de recibo não são válidas. |
| `err.entity_map_invalid` | The account-to-company settings are not valid. | As configurações de conta por empresa não são válidas. |
| `err.intake_domain_invalid` | The e-mail domain is a bare name, without an @. | O domínio de e-mail é apenas o nome, sem @. |
| `err.intake_aliases_invalid` | Each e-mail name maps to one person's name. | Cada nome de e-mail corresponde ao nome de uma pessoa. |
| `err.intake_number_invalid` | {field} has to be a whole number above zero. | {field} precisa ser um número inteiro maior que zero. |
| `err.intake_alert_recipients_invalid` | Alerts only go to @brisken.com addresses. | Os alertas vão apenas para endereços @brisken.com. |
| `err.intake_known_senders_invalid` | Each known sender is one plain e-mail address. | Cada remetente conhecido é um endereço de e-mail simples. |
| `err.intake_known_senders_too_many` | At most {limit} known senders. | No máximo {limit} remetentes conhecidos. |
| `err.intake_travel_alias_invalid` | The travel address is just the part before the @ (letters, numbers, . _ -). | O endereço de viagem é apenas a parte antes do @ (letras, números, . _ -). |
| `err.intake_travel_alias_reserved` | "receipts" is the company address; choose another name for travel. | "receipts" é o endereço da empresa; escolha outro nome para viagens. |
| `err.intake_travel_alias_collision` | "{alias}" is already one person's e-mail name. | "{alias}" já é o nome de e-mail de uma pessoa. |
| `err.memory_row_key_required` | Choose the company and the supplier. | Escolha a empresa e o fornecedor. |
| `err.memory_category_not_found` | The tool has learned nothing for that company and supplier. | A ferramenta não aprendeu nada para essa empresa e esse fornecedor. |
| `err.memory_rows_required` | Choose at least one row. | Escolha pelo menos uma linha. |
| `err.memory_rows_invalid` | None of those rows could be read. | Nenhuma dessas linhas pôde ser lida. |
| `err.comment_required` | Write a note first. | Escreva uma observação primeiro. |
| `err.mail_not_found` | This e-mail no longer exists. | Este e-mail não existe mais. |
| `err.mail_not_travel` | Only travel e-mail joins a trip; e-mail for a month joins its month on its own. | Somente e-mails de viagem entram em uma viagem; os e-mails de um mês entram sozinhos no mês deles. |
| `err.mail_travel_not_month` | Travel e-mail joins a trip, not a month. | E-mails de viagem entram em uma viagem, não em um mês. |
| `err.mail_no_file_yet` | This e-mail has no file yet. Turn its body into a PDF first. | Este e-mail ainda não tem arquivo. Transforme o corpo dele em PDF primeiro. |
| `err.mail_no_attachment` | This e-mail delivered no attachment. Turn its body into a PDF instead. | Este e-mail não trouxe anexo. Transforme o corpo dele em PDF. |
| `err.mail_no_readable_body` | There is no readable text in this e-mail. | Não há texto legível neste e-mail. |
| `err.mail_not_renderable` | Only held e-mail without an attachment can be turned into a PDF. | Somente e-mails retidos e sem anexo podem virar PDF. |
| `err.mail_not_duplicate` | This e-mail is not being held as a duplicate. | Este e-mail não está retido como duplicado. |
| `err.mail_not_dismissable` | Only held or waiting e-mail can be dismissed. | Somente e-mails retidos ou em espera podem ser descartados. |
| `err.mail_month_still_live` | This e-mail still belongs to a month that exists. | Este e-mail ainda pertence a um mês que existe. |
| `err.mail_state_conflict` | This e-mail has already moved on. Reload the page to see where it is. | Este e-mail já mudou de situação. Recarregue a página para ver onde ele está. |
| `err.mail_custody_unreadable` | The stored copy of this e-mail cannot be read. | A cópia armazenada deste e-mail não pode ser lida. |
| `err.no_open_month` | There is no open month to add this to. | Não há mês aberto para adicionar isto. |
| `err.mail_ingest_failed` | Reading this e-mail failed. It stays where it is; try again. | A leitura deste e-mail falhou. Ele continua onde está; tente de novo. |
| `err.mail_render_failed` | Turning this e-mail into a PDF failed. Try again. | Não foi possível transformar este e-mail em PDF. Tente de novo. |
| `err.trip_join_failed` | Adding this e-mail to the trip failed. It went back to waiting; try again. | Não foi possível adicionar este e-mail à viagem. Ele voltou para a espera; tente de novo. |
| `err.mail_routing_failed` | This e-mail could not be filed. It is held and can be retried. | Não foi possível arquivar este e-mail. Ele está retido e pode ser reprocessado. |

### Advisories (`adv.*`)

| Key | EN | PT-BR |
|---|---|---|
| `adv.fx_rate_missing` | {n_receipts} receipts are in {currency} and there is no {currency} to {card_currency} rate, so they cannot be matched automatically. | {n_receipts} recibos estão em {currency} e não há taxa de {currency} para {card_currency}, então eles não podem ser conciliados automaticamente. |
| `adv.no_chart_of_accounts` | No chart of accounts was found for this month, so the accounts are not checked and the export writes a placeholder. | Nenhum plano de contas foi encontrado para este mês, então as contas não são verificadas e a exportação grava um espaço reservado. |
| `adv.card_posting_account_missing` | The card {card} has no posting account (optional: only the export uses it). | O cartão {card} não tem conta contábil (opcional: só a exportação a usa). |
| `adv.fx_rate_drift` | The {pair} rate set in Settings ({settings_rate}) is {gap_pct}% away from the ECB average for {ecb_month} ({ecb_rate}). A rate set in Settings wins over the ECB for this month's {n_receipts} receipts; removing it lets the ECB average apply. | A taxa {pair} definida em Configurações ({settings_rate}) está {gap_pct}% distante da média do BCE de {ecb_month} ({ecb_rate}). Uma taxa definida em Configurações prevalece sobre a do BCE para os {n_receipts} recibos deste mês; ao removê-la, a média do BCE passa a valer. |
| `adv.statement_not_pdf` | {n_foreign} of {n_receipts} receipts are in another currency but the statement is {suffix}. The bank's PDF statement carries each charge's original amount, which lets these match on their own. | {n_foreign} de {n_receipts} recibos estão em outra moeda, mas o extrato é {suffix}. O extrato em PDF do banco traz o valor original de cada lançamento, o que permite a conciliação automática. |
| `adv.statement_account_differs` | This card's earlier statement ({other_file}) was read as account {other_account} and this one as {account}, so anything in both files is in the month twice. Check the account number. | O extrato anterior deste cartão ({other_file}) foi lido como conta {other_account} e este como {account}, então tudo que estiver nos dois arquivos aparece duas vezes no mês. Confira o número da conta. |
| `adv.statement_period_overlap` | All {n_rows} charges in this file are new, but {other_file} already covers {period_start} to {period_end} on the same account. If this is the same statement exported again, the month now holds both readings. | Todos os {n_rows} lançamentos deste arquivo são novos, mas {other_file} já cobre de {period_start} a {period_end} na mesma conta. Se este for o mesmo extrato exportado de novo, o mês agora tem as duas leituras. |

### Row chips (`warn.*`)

| Key | EN | PT-BR |
|---|---|---|
| `warn.amountMismatch` | amount differs | valor diferente |
| `warn.dateMismatch` | date differs | data diferente |
| `warn.nearMiss` | near miss | quase igual |
| `warn.currencyUnknown` | currency unknown | moeda desconhecida |

## Do not change

The requests themselves, the `error` field the backend sends (it stays the fallback), `month_health` rendering, `uploadIssues.ts` (already localized off its own codes, item 20), the PDF and CSV downloads (they are English on purpose: the auditor reads English), and the failure reporting in `error-capture.ts` / `lovable-error-reporting.ts`.

## Checking it landed

1. Bundle (`uv run tools/lovable-bundle-audit.py`, controls must hit): `errorText` and `err.` keys in a non-i18n chunk; `err.company_card`, `err.batch_deleted`, `err.run_not_found`, `adv.no_chart_of_accounts`, `adv.fx_rate_drift`, `warn.amountMismatch` and the PT sentence "Este mês foi excluído enquanto você trabalhava nele" in `chunk-i18n`; `data-pt` and `brisken.lang` in the entry chunk (the crash page).
2. Sign in, switch the language to Portuguese, open July (`/runs/50622baec444`). Read the amber "setup" box: it is Portuguese, and the numbers in it match the API's `summary.setup_advisories`.
3. On the same page, a row with a chosen candidate whose amount is not exact shows the chip "valor diferente" (English: "amount differs"); hover it and the tooltip is Portuguese too.
4. Read-only refusal drive, no write: open `/runs/does-not-exist`. The screen says "Este mês não existe mais." (EN: "This month no longer exists."). Switch to English and reload: the same screen reads the English sentence.
5. Crash page: with the language set to Portuguese, open a URL the SSR cannot render (or throttle the network so the entry chunk fails). The page reads "Esta página não carregou".
6. Network tab through the whole drive: no PUT, POST, PATCH or DELETE except `POST /api/login`.
````
