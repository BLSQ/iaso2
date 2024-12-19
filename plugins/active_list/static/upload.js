var monthSelect = $('#monthSelect')
var countrySelect = $('#countrySelect');
var regionSelect = $('#regionSelect')
var districtSelect = $('#districtSelect')
var facilitySelect = $('#facilitySelect')
var link = $('#link')

regionSelect.hide()
districtSelect.hide()
facilitySelect.hide()
link.hide()

monthSelect.on('change', function () {
  $('#period').val(this.value)
})

$.getJSON('/api/orgunits/tree/?validation_status=VALID&ignoreEmptyNames=true', function (data) {

  fillSelect('#countrySelect', data);
  countrySelect.show();
});

countrySelect.on('change', function () {
  regionSelect.hide();
  districtSelect.hide();
  facilitySelect.hide();

  $.getJSON('/api/orgunits/tree/?&parent_id=' + this.value + '&validation_status=VALID&ignoreEmptyNames=true', function (data) {
    fillSelect('#regionSelect', data);
    regionSelect.show();

  });
});

regionSelect.on('change', function () {
  districtSelect.hide()
  facilitySelect.hide()
  link.hide()
  $.getJSON('/api/orgunits/tree/?&parent_id=' + this.value + '&validation_status=VALID&ignoreEmptyNames=true', function (data) {
    fillSelect('#districtSelect', data)
    districtSelect.show()

  })
})

districtSelect.on('change', function () {
  facilitySelect.hide()
  link.hide()
  $.getJSON('/api/orgunits/tree/?&parent_id=' + this.value + '&validation_status=VALID&ignoreEmptyNames=true', function (data) {
    console.log(data)
    fillSelect('#facilitySelect', data)
    facilitySelect.show()

  })
})

facilitySelect.on('change', function () {
  $('#org_unit_id').val(this.value)
  link.show()
})

$(document).ready(function () {
  $('form').submit(function (event) {
    event.preventDefault()

    var formData = new FormData(this)

    submitForm(formData)
  })

  fillSelectWithMonths()
})