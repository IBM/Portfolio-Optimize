var apiUrl = location.protocol + '//' + location.host + location.pathname + "api/";
//var apiUrl = "http://localhost:8080/api/";

//update interface with portfolios and risk factors
var display=["loader_section","section_one","section_two","section_three","section_four","section_five"];
var allocationConstraintsData;
var currDisplay=0;
$(document).ready(function() {
        $("#next_button").html("Lets Get Building");
        loadDisplay(false);
        $("#message").text("Loading Initial Data..");
        $.ajax({
            url: apiUrl + 'load',
            contentType: 'application/json',
            success: function(data) {
                loadSelectValues("user_portfolio_name",data.user_portfolios);
                loadSelectValues("benchmark",data.benchmark_portfolios);
                loadHardConstraints(data.hard_constraints);
                loadESGConstraints(data.esg_constraints);
                loadAllocationData(data.allocation_constraints);
                loadDisplay(true);
              },
              error: function(jqXHR, textStatus, errorThrown) {
                  alert("Failed to initialize application.");
                  console.log(errorThrown);
                  console.log(textStatus);
                  console.log(jqXHR);
          }});
});

$('#home').click(function() {
  location.reload();
});

function loadDisplay(value) {
    if(value){
      if(validations(currDisplay)){
        currDisplay++;
        if(currDisplay==1){
          $("#loader_section").hide();
          $("#button_section").show();
        }
        $("#"+display[currDisplay]).show();
      }
    }else{
      $("#button_section").hide();
       $("#loader_section").show();
       for(var i=1;i<display.length;i++){
           $("#"+display[i]).hide();
       }
    }
}

function validations(value){
//  console.log(value +"  value received");
    switch (value) {
      case 1: return validatePortfolio(false,{});
              break;
      case 2: return validateBenchMark(false,{});
              break;
      case 3: return validateESG(false,{});
              break;
      case 4: return validateConcentrations();
              break;
      default: return true;

    }
}

function capitalize(s) {
    return s[0].toUpperCase() + s.substr(1);
}

function loadSelectValues(selectId,names) {
    for(var  i=0;i<names.length;i++){
        $('#'+selectId).append("<option value=" + names[i] +">" + names[i] +"</option>");
    }
}

function validatePortfolio(flag,query){
    var portfolioType= $('input[name=user_portfolio]:checked').val();
    var portfolioName="";
    if(portfolioType==='existing'){
        portfolioName=$('#user_portfolio_name').val();
        if(portfolioName===""){
          alert("Select your existing portfolio");
          return false;
        }
    }
    if(flag){
      query["user_portfolio"]={"Type":portfolioType,"Name":portfolioName};
    }else{
      $("#next_button").html("Next");
    }
    return true;
}

function validateBenchMark(flag,query) {
    var benchmark = $("#benchmark").val();
    if(benchmark===""){
      alert("Select a benchmark portfolio");
      return false;
    }
    if(flag){
      var hardConstraintsData=$("#hard_constraints th");
      var hardConstraints=[];
      for(var i=0;i<hardConstraintsData.length;i++){
          /*var value= $('input[name='+hardConstraintsData[i].innerText.toLowerCase()+']:checked').val();*/
          var value= $("input[name='"+hardConstraintsData[i].innerText+"']:checked").val();
          if(value!==""){
              hardConstraints.push("has_"+hardConstraintsData[i].innerText);
          }
      }
      query["benchmark"]=benchmark;
      query["hard_constraints"]=hardConstraints;
    }
    return true;
}

function validateESG(flag,query) {
  if(flag){
    var esgConstraints=[];
    var identifiers = $('input[name=esg_checkbox]:checked');
    for(var i=0;i<identifiers.length;i++){
        var id  = identifiers[i].value;
        var value = $("#"+id+"_type").text().trim()//.toLowerCase();
        esgConstraints.push({"type":"esg_"+value,"value": $('input[name='+id+'_value]:checked').val()});
    }
    query["esg_constraints"]=esgConstraints;
  }
  else {
      $("#next_button").html("Optimize");
  }
  return true;
}

function validateConcentrations() {
  var query={};
  if(validatePortfolio(true,query)  && validateBenchMark(true,query) && validateESG(true,query)){
    //Check to see that user put in an amount if starting from scratch.
    if($('input[name=user_portfolio]:checked').val() == "new"){
        if($("#cash_infusion_checkbox").is(':checked') == false || $('#cash_infusion').val() == "" ){
            alert("Please enter the amount you're looking to invest, since you're starting from scratch. This is entered as a cash infusion under result requirements. Make sure the constraint is activated by checking the box!")
            return false;
        }
    }
    var allocationConstraints =[];
    var identifiers = $('input[name=allocation_checkbox]');
    for(var i=0;i<identifiers.length;i++){
        var id  = identifiers[i].id.split('_')[0];
        allocationConstraints.push({"type":($('#'+id+'_constraints  :selected').text()).trim(),"value":($('#'+id+'_values :selected').text()).trim(),"allocation":Number($('#'+id+'_allocation').val())*0.01,"inequality":$('#'+id+'_inequality').val()});
    }
    query["allocation_constraints"]=allocationConstraints;
    var resultRequirements =[];
    if($("#cash_infusion_checkbox").is(':checked')){
      var cashInfusion=Number($('#cash_infusion').val());
      if(cashInfusion>0){
         resultRequirements.push({"type":"CashInfusion","value":cashInfusion});
      }
    }
    if($("#short_sales_checkbox").is(':checked')){
      resultRequirements.push({"type":"AllowShortSales","value":$('input[name=short_sales]:checked').val()});
    }
    if($("#investment_weight_checkbox").is(':checked')){
      var maximumInvestmentWeight = Number($('#investment_weight').val())*0.01;
      if(maximumInvestmentWeight>0){
        resultRequirements.push({"type":"MaximumInvestmentWeight","value":maximumInvestmentWeight});
      }
    }
    if($("#max_positions_checkbox").is(':checked')){
      var maximumNumberofPositions = Number($('#max_positions').val());
      if(maximumNumberofPositions>0){
        resultRequirements.push({"type":"MaximumNumberofPositions","value":Number(maximumNumberofPositions)});
      }
    }

    if($("#min_postions_checkbox").is(':checked')){
      var minimumNumberofPositions =Number($('#min_postions').val());
      if(minimumNumberofPositions >0){
        resultRequirements.push({"type":"MinimumNumberofPositions","value":Number(minimumNumberofPositions)});
      }
    }
    query["result_requirements"]=resultRequirements;
    $("#message").text("Your optimization will be completed shortly.");
    $("#button_section").hide();
    $("#loader_section").show();
    return optimize(query);
  }
  else{
    return false;
  }
}

function optimize(query){
  console.log("User Query : ");
  console.log(query);
  $.ajax(
            {
                url:apiUrl + 'optimize',
                type: "POST",
                data: JSON.stringify(query),
                dataType: 'json',
                //async: false,
                contentType: 'application/json; charset=utf-8',
                success: function(results) {
                    topFunction()
                    console.log("Optimization Results :");
                    console.log(results);
                    //$('#results > tr').remove();
                    var all_tradeit_trades = { trades: [] };
                    $('#difference').append('<br><br><p style="width: 75%"> An optimal portfolio was constructed with a volatility that differs from the benchmark by only '+ formatNumber(results.Metadata.ObjectiveValue,10)+'. The following are the trades required to arrive at this optimized portfolio and the resulting allocation:</p>');
                    var holdings_title = 'Results of the Optimization:';
                    $('.title1 h3').text(holdings_title);
                    if(results.Holdings.length>0){
                      var rowData="<tr>";
                      var tableCols=[];
                      $.each(results.Holdings[0], function(key, value) {
                            //console.log(key, value);
                            if(capitalize(key).trim()!="Asset"){
                                tableCols.push(key);
                                switch(capitalize(key)) {
                                    case "OptimizedQuantity":
                                        var f = "New Quantity";
                                        break;
                                    case "OptimizedTrade":
                                        var f = "Suggested Trade";
                                        break;
                                    default:
                                        var f = capitalize(key)
                                }
                                rowData+="<td><b>"+f+"</b></td>";
                            }
                      });
                      $(".port-table  thead").html(rowData+"</tr>");
                      var rowData="";
                      for (var i = 0; i < results.Holdings.length; i++) {
                        rowData+="<tr>";
                        var tradeit_trade = {};
                        for(var j=0;j<tableCols.length;j++){

                          var value = results.Holdings[i][tableCols[j]];
                         
                          if(typeof value == 'number'){
                          	if (value % 1 != 0) {
                              value = value.toFixed(2);
                            }
                            value = commaFormat(value);
                          }

                          //'OptimizedTrade' assign green/reg
                         if(tableCols[j] == "OptimizedQuantity"){
                            if(results.Holdings[i]["OptimizedTrade"] < 0){
                                rowData+='<td class="red">'+value+"</td>";
                            }else if(results.Holdings[i]["OptimizedTrade"] > 0){
                                rowData+='<td class="green">'+value+"</td>";
                            }else{
                                rowData+="<td>"+value+"</td>";
                            }
                        }else if(tableCols[j] == "OptimizedTrade"){ //Trades to make
                            if(value<0){
                                if(results.Holdings[i]["OptimizedTrade"] == -1*results.Holdings[i]["Quantity"]){
                                    tradeit_trade.quantity = value.substring(1);
                                    tradeit_trade.action = "sell";
                                    value = "Close this position."
                                    rowData+="<td>"+value+"</td>"; 
                                }else{
                                    tradeit_trade.quantity = value.substring(1);
                                    tradeit_trade.action = "sell";
                                    value = "Sell "+value.substring(1)+" shares."
                                    rowData+="<td>"+value+"</td>"; 
                                }
                            }else if(value>0){
                                tradeit_trade.quantity = value;
                                tradeit_trade.action = "buy";
                                value = "Buy "+value+" shares."
                                rowData+="<td>"+value+"</td>"; 
                            }else{
                                tradeit_trade.quantity = value;
                                tradeit_trade.action = "buy";
                                rowData+="<td>"+value+"</td>"; 
                            }
                        }else{
                            if (j == 0) {
                              tradeit_trade.name = value;
                            }
                            rowData+="<td>"+value+"</td>";
                        }
                         //owData+="<td>"+value+"</td>";
                        }
                        all_tradeit_trades.trades.push(tradeit_trade);
                        rowData+="</tr>";
                      }
                      $(".port-table  tbody").html(rowData);
                      $('#results').DataTable( {
                          columnDefs: [ {
                              targets: [ 0 ],
                              orderData: [ 0, 1 ]
                          }, {
                              targets: [ 1 ],
                              orderData: [ 1, 0 ]
                          }, {
                              targets: [ 4 ],
                              orderData: [ 4, 0 ]
                          } ]
                      } );
                    }
                    $("#loader_section").hide();
                    $("#section_one").hide();
                    $("#section_two").hide();
                    $("#section_three").hide();
                    $("#section_four").hide();
                    $("#section_five").show();
                    //loadDisplay(4);
                    $("#make_tradeit_trades").show();
                    $("#make_tradeit_trades").click(function() {
                      var redirect = "http://portfolio-tradeit.mybluemix.net";
                      $.redirect(redirect, { postdata: JSON.stringify(all_tradeit_trades) }, "POST", "_blank");
                    });
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    $("#loader_section").hide();
                    alert("Optimization unsuccessful. Either no optimal solution was found, or something went wrong with the request. Please try again.");
                    console.log(errorThrown);
                    console.log(textStatus);
                    console.log(jqXHR);
                    location.reload();
                }
            }
            
        );
    return false;
    
}

function loadHardConstraints(values) {
    var columnWidth = '100%';
    if(values.length>0){
        columnWidth =  (100/values.length)+'%';
    }
    //console.log(columnWidth);
    var table_headers="";
    var table_description="";
    var table_options="";
    for(var  i=0;i<values.length;i++){
        var type = values[i].type;
        //console.log(type);
        type= type.substring((type.indexOf('_')+1));
        //console.log(type);
        table_headers+="<th>"+capitalize(type)+"</th>";
        table_description+="<td width="+columnWidth+"><br>"+values[i].description+"</td>";
        table_options+="<td width="+columnWidth+"><br><input type='radio' name='"+type+"' value='' checked='checked'>Add these stocks<br> <input type='radio' name='"+type+"' value='has_"+type+"'>Remove these stocks<br></td>";
    }
    $('<tr>').html(table_headers).appendTo('#hard_constraints');
    $('<tr>').html(table_description).appendTo('#hard_constraints');
    $('<tr>').html(table_options).appendTo('#hard_constraints');
}

function loadESGConstraints(values) {
    for(var  i=0;i<values.length;i++){
        var type = values[i].type;
        type=type.substring((type.indexOf('_')+1));
        var id=Math.floor(Math.random() * 90000) + 10000;
        $("#esg_constraints > tbody").append("<tr id="+id+"><td>&nbsp;&nbsp;&nbsp;<input type='checkbox' name='esg_checkbox' value="+id+"></td><td width='50%'><br><p id='"+id+"_type'><b>"+capitalize(type)+" </b></p>"+values[i].description+"</td><td><br><div class='btn-group btn-group-2' data-toggle='buttons'> "+
        "<label class='btn btn-default active'> <input type='radio' name='"+id+"_value' value='Low' checked='checked'>Low"+
        "</label><label class='btn btn-default'> <input type='radio' name='"+id+"_value' value='Average'>Medium"+
        "</label><label class='btn btn-default'> <input type='radio' name='"+id+"_value' value='High'>High</label></td></tr>");
    }
}

function loadAllocationData(values){
    allocationConstraintsData=values;
    addConstraintRow(allocationConstraintsData)
}

function addConstraintRow(values) {
    var id= Math.floor(Math.random() * 90000) + 10000;
    var tableRow="<tr id="+id+"><td width='5%'>&nbsp;&nbsp;&nbsp;<input type='checkbox' name='allocation_checkbox' id='"+id+"_check' checked></td><td width='20%'><select style='width:90%' id='"+id+"_constraints' class='custom-select' onchange='loadAllocationValues(this.value,this.id)'>";
    for(var i=0;i<values.length;i++){
      tableRow+="<option value='" + values[i].type +"'> " + values[i].type + "</option>";
    }
    tableRow+="</select></td><td width='20%'><select style='width:90%' id='"+id+"_values' class='custom-select'>";
    var constraintValues=values[0].values;
    for(var i=0;i<constraintValues.length;i++){
        tableRow+="<option value='"+constraintValues[i]+"'> " +constraintValues[i] + "</option>";
    }

    tableRow+="</select></td><td ><div style='width: 95%'><input type='range' min='0' max='100' value='20' id='"+id+"_allocation'></div></td><td><p id='"+id+"_range'>20</p></td><td><select id='"+id+"_inequality' class='custom-select'>"+
                "<option selected='selected' value='less-or-equal'>less than or equal</option><option value='greater-or-equal'>greater than or equal</option>"+
                "</select></td></tr>";
      $("#allocation_table > tbody").append(tableRow);
      $("#"+id+"_allocation").on("change",function(){
            $("#"+id+"_range").text($(this).val());
      });
}

function addConstraint(){
    addConstraintRow(allocationConstraintsData);
}

function deleteConstraint(){
    var selectedRows = $('input[name=allocation_checkbox]:checked');
    if(selectedRows.length==0){
        alert("Select Constraint to delete");
        return;
    }
    for(var i=0;i<selectedRows.length;i++){
        $("#"+selectedRows[i].id.split('_')[0]).closest('tr').remove();
    }
}

function loadAllocationValues(selected,selectId){
  selectId=selectId.split('_')[0]+'_values';
  var input =allocationConstraintsData;
  $("#"+selectId).find("option").remove();
  for(var  i=0;i<input.length;i++){
      if(input[i].type==selected){
          loadSelectValues(selectId,input[i].values);
          break;
      }
  }
}

function formatNumber(val,decimalPlaces){
  return  Number(val).toFixed(decimalPlaces);
}

const commaFormat = (x) => {
    var v = x.toString().split(".");
    v[0] = v[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    return v.join(".");
}

// When the user clicks on the button, scroll to the top of the document
function topFunction() {
    document.body.scrollTop = 0; // For Safari
    document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
}
