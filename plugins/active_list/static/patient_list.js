var monthSelect = $('#monthSelect')
var countrySelect = $('#countrySelect')
var regionSelect = $('#regionSelect')
var districtSelect = $('#districtSelect')
var facilitySelect = $('#facilitySelect')
var modeSelect = $('#modeSelect')
var dataContainer = $('#dataContainer')
regionSelect.hide()
districtSelect.hide()
facilitySelect.hide()
dataContainer.hide()
monthSelect.on('change', function () {
  $('#period').val(this.value)
})

$.getJSON('/api/orgunits/tree/?validation_status=VALID&ignoreEmptyNames=true', function (data) {

  fillSelect('#countrySelect', data)
  countrySelect.show()
})

countrySelect.on('change', function () {
  regionSelect.hide()
  districtSelect.hide()
  facilitySelect.hide()
  dataContainer.hide()
  $.getJSON('/api/orgunits/tree/?&parent_id=' + this.value + '&validation_status=VALID&ignoreEmptyNames=true', function (data) {
    fillSelect('#regionSelect', data)
    regionSelect.show()
    dataContainer.hide()
  })
})

regionSelect.on('change', function () {
  districtSelect.hide()
  facilitySelect.hide()
  dataContainer.hide()
  $.getJSON('/api/orgunits/tree/?&parent_id=' + this.value + '&validation_status=VALID&ignoreEmptyNames=true', function (data) {
    fillSelect('#districtSelect', data)

    districtSelect.show()
    dataContainer.hide()
  })
})
districtSelect.on('change', function () {
  facilitySelect.hide()
  dataContainer.hide()
  $.getJSON('/api/orgunits/tree/?&parent_id=' + this.value + '&validation_status=VALID&ignoreEmptyNames=true', function (data) {
    fillSelect('#facilitySelect', data)
    facilitySelect.show()
  })
})

function refreshData () {
  var orgUnitId = facilitySelect.val()
  var period = monthSelect.val()
  var mode = modeSelect.val()
  var url = '/active_list/patient_list_api/' + orgUnitId + '/' + period + '/?mode=' + mode
  $.getJSON(url, function (data) {
    var table = generateTable(data.table_content)

    $('#table-container').html(table)
    console.log(url)
    var excel_link = $('#excel_link')
    if (data.table_content.length === 0) {
      excel_link.hide()
      $('#nodata').show()
    } else {
      excel_link.attr('href', url + '&xls=true')
      excel_link.show()
      $('#nodata').hide()
    }
    $('#generatedTable').tablesorter()
    dataContainer.show()
  })
}

facilitySelect.on('change', function () {
  refreshData()
})
monthSelect.on('change', function () {
  refreshData()
})
modeSelect.on('change', function () {
  refreshData()
})

$(document).ready(function () {
  $('form').submit(function (event) {
    event.preventDefault()
  })

  fillSelectWithMonths()
})

$(document).ready(function () {
  fillSelectWithMonths()
})