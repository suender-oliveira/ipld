function refreshPage() {
  location.reload();
}

$("#datatable_results").DataTable({
  dom: "Bfrtip",
  responsive: true,
  pageLength: 50,
  searching: true,
  search: {
    regex: true,
  },
  buttons: ["copy", "excel"],
});

$(document).ready(function () {
  $.extend($.fn.dataTable.defaults, {
    responsive: true,
    pageLength: 50,
    searching: true,
    search: {
      regex: true,
    },
  });
  $("#datatable_load").DataTable();
});

$(document).ready(function () {
  $.extend($.fn.dataTable.defaults, {
    responsive: true,
    pageLength: 10,
    searching: true,
    search: {
      regex: true,
    },
  });
  $("#datatable_load_10").DataTable();
});

const tooltipTriggerList = document.querySelectorAll(
  '[data-bs-toggle="tooltip"]'
);
const tooltipList = [...tooltipTriggerList].map(
  (tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl)
);

let isChecked = true;

function checkAll(ids) {
  let inputs = document.querySelectorAll(".form-check-input");
  for (const element of inputs) {
    if (ids.includes(element.id)) {
      element.checked = isChecked;
    }
  }
  isChecked = !isChecked;
}

function socketIORender(data) {
  let html = "<h6>Overall progress of completed tasks</h6>";

  html +=
    '<div class="progress" role="progressbar" aria-label="Animated striped example"';
  html +=
    ' aria-valuenow="' +
    Math.floor(data.percent) +
    '" aria-valuemin="0" aria-valuemax="100">';
  html +=
    '<div class="progress-bar progress-bar-striped progress-bar-animated" ';
  html +=
    'style="width: ' +
    Math.floor(data.percent) +
    '%">' +
    Math.floor(data.percent) +
    "%</div>";
  html += "</div><br>";

  html += '<ul class="list-group">';

  let tasks = data.result;
  for (const task of tasks) {
    const [key, value] = task.split(": ").map((str) => str.replace(/'/g, ""));
    html +=
      '<li class="list-group-item d-flex justify-content-between align-items-center">';
    if (value === "done") {
      html += '<span class="text-success fw-bold">';
      html += key;
      html += "</span>";
      html += '<span class="badge bg-success rounded-pill">Done</span>';
    } else if (value === "error") {
      html += '<span class="text-danger fw-bold">';
      html += key + '<small class="text-muted"> (' + data.error + ") </small>";
      html += "</span>";
      html += '<span class="badge bg-danger rounded-pill"> Fail </span>';
    } else if (value === "wait") {
      html += '<span class="text-warning fw-bold">';
      html += key;
      html += "</span>";
      html += '<span class="placeholder-glow">';
      html +=
        '<span class="badge text-dark bg-warning rounded-pill placeholder">Wait</span>';
      html += "</span>";
      html += '<span class="visually-hidden">Carregando...</span>';
      html += "</div>";
    }
    html += "</li>";
  }

  html += "</ul>";

  document.getElementById("task-progress").innerHTML = html;
}

function socketIORenderDryRun(data) {
  let got_error;
  const error_msg = {
    firewall_rules:
      "Verify that there is an approved firewall flow in Cirrus portal.",
    check_ssh_login: "Check your credentials and try again.",
    check_dataset_access:
      "Check your dataset granted permissions and try again.",
    check_tmp_space:
      "Check if there is left free space on /tmp filesystem and try again.",
  };
  let html = "<h6>Overall progress of dry run checks</h6>";

  html += '<ul class="list-group">';

  for (let key in data) {
    if (data.hasOwnProperty(key)) {
      html +=
        '<li class="list-group-item d-flex justify-content-between align-items-center">';

      let task = data[key];

      if (task === "done") {
        got_error = 0; // Assign value to got_error
        html += `<span class="text-success fw-bold">[ ${key} ]</span><span class="badge bg-success rounded-pill">Done</span>`;
      } else if (task === "error") {
        got_error = 1; // Assign value to got_error
        html += `<span class="text-danger fw-bold">[ ${key} ]<small class="text-muted">${errorMsg[key]}</small></span><span class="badge bg-danger rounded-pill">Fail</span>`;
        break;
      } else if (task === "wait") {
        got_error = 2; // Assign value to got_error
        html += `<span class="text-warning fw-bold">[ ${key} ]</span><span class="placeholder-glow"><span class="badge text-dark bg-warning rounded-pill placeholder">Wait</span><span class="visually-hidden">Loading...</span></div>`;
      }
    }

    html += "</li>";
  }

  html += "</ul>";

  document.getElementById("dry-run").innerHTML = html;

  if (got_error === 1) {
    let html_error = '<div class="col-sm-2">';
    html_error +=
      '<a href="/lpar/settings/new/step-1" class="btn btn-sm btn-outline-dark w-100"><i class="bi bi-arrow-left-square"></i> &nbsp; Back</a>';
    html_error += "</div>";
    html_error += '<div class="col-sm-2">';
    html_error +=
      '<button type="button" class="btn btn-sm btn-dark w-100" onclick="refreshPage()" ><i class="bi bi-journal-code"></i> &nbsp; Dry run</button>';
    html_error += "</div>";

    document.getElementById("din_buttons").innerHTML = html_error;
  } else if (got_error === 2) {
    let html_error = '<div class="col-sm-2">';
    html_error += "<span></span>";
    html_error += "</div>";
  } else {
    let html_error = '<div class="col-sm-2">';
    html_error +=
      '<a href="/lpar/settings/new/step-1" class="btn btn-sm btn-outline-dark w-100"><i class="bi bi-arrow-left-square"></i> &nbsp; Back</a>';
    html_error += "</div>";
    html_error += '<div class="col-sm-2">';
    html_error +=
      '<button type="submit" class="btn btn-sm btn-dark w-100"><i class="bi bi-save"></i> &nbsp; Save</button>';
    html_error += "</div>";

    document.getElementById("din_buttons").innerHTML = html_error;
  }
}

function call_dry_run(lpar, hostname, dataset, user_id, csrf_token) {
  const url = "/lpar/settings/dry-run";

  const formData = new FormData();
  formData.append("lpar", lpar);
  formData.append("hostname", hostname);
  formData.append("dataset", dataset);
  formData.append("user_id", user_id);

  fetch(url, {
    method: "POST",
    headers: { "X-CSRFToken": csrf_token },
    body: formData,
  });
}
