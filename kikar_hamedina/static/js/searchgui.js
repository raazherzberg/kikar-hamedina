$(document).ready(function () {

    $(".glyphicon-trash").parent().click(function () {
        $('#searchgui-text-input').val('')
        $('#search-gui-result-list').html('')
        $('#search-gui-member-added-list').html('')
        $('#search-gui-party-added-list').html('')
        $('#search-gui-tag-added-list').html('')
    })

    $("#searchgui-go-button").hover(function () {
        $(this).toggleClass("alert-info")
    })

    $("#searchgui-go-button").click(function () {
        console.log("hERE")


        if ($(".result-info").length > 0 || $('#searchgui-text-input').val().length > 0) {
            searchTerms = {'member': [], 'party': [], 'tag': [], 'search_str': []}
            $(".result-info").each(function () {
                type = $(this).data('type')
                id = $(this).data('id')
                searchTerms[type].push(id)
            })
            url = "/search/?"
            member_ids = searchTerms['member'].join(',')
            if (member_ids.length > 0) {
                url += "members=" + member_ids + "&"
            }
            party_ids = searchTerms['party'].join(',')
            if (party_ids.length > 0) {
                url += "parties=" + party_ids + "&"
            }
            tag_ids = searchTerms['tag'].join(',')
            if (tag_ids.length > 0) {
                url += "tags=" + tag_ids + "&"
            }

            inputValue = $('#searchgui-text-input').val()
            if (inputValue.length > 0) {
                searchTerms['search_str'].push(inputValue)
            }
            search_str_ids = '"' + searchTerms['search_str'].join('","') + '"'
            console.log(search_str_ids)
            if (search_str_ids.length > 2) {
                // length > 2 - empty string will be "" //
                url += "search_str=" + search_str_ids + "&"
            }
            console.log(url)
            var operator = $("input:radio[name=selected-operator]:checked").val()
            //        console.log(operator).delay(5000)
            url += "tags_and_search_str_operator=" + operator
            window.location.assign(encodeURI(url))
        } else {
            $("#searchgui-text-input").attr("placeholder", 'צריך לחפש משהו בשביל למצוא משהו')
        }
    })

    $("#searchgui-add-word").click(function () {
        if ($('#searchgui-text-input').val().length > 0) {
            context = {}
            context['name'] = $('#searchgui-text-input').val()
            context['id'] = $('#searchgui-text-input').val()
            $("#searchgui-add-word").data('word-num', context['id'] + 1)
            context['type'] = 'search_str'
            context['icon'] = 'comment'
            var source = $("#search-gui-added-list-item-template").html()
            var template = Handlebars.compile(source);
            var html = template(context);
            $('#searchgui-search-words').append(html)

            addedElement = $('#searchgui-search-words').find("#" + context['type'] + context['id'])
            addedElement.find(".glyphicon-remove").parent().click(function () {
                $('#searchgui-search-words').find("#" + context['type'] + context['id']).remove()
                searchgui_objects_visibility()
            })
            addedElement.find(".glyphicon-remove").parent().hover(function () {
                $(this).toggleClass("alert-danger")
            })
            addedElement.hover(function () {
                $(this).find(".glyphicon-" + context['icon']).parent().toggleClass("alert-success")
                $(this).find(".glyphicon-remove").parent().toggleClass("hidden-badge")
            })


            $('#searchgui-text-input').val('')
            searchgui_objects_visibility()
        }
    })


    $('#searchgui-text-input').keydown(function () {
        inputValue = $('#searchgui-text-input').val()

        url = "/search_bar/?text=" + inputValue
        if (inputValue.length > 1) {
            $.ajax({
                url: url,
                contentType: "application/json",
                success: function (data) {
                    $('#search-gui-result-list').html('')
                    for (var i = 0; i < data['number_of_results']; i++) {
                        var result = data['results'][i]
                        resList = $('#search-gui-' + result['type'] + '-added-list').find("#" + result['type'] + result['id'])
                        if (resList.size() > 0) {
                            continue;
                        }
                        var source = $("#search-gui-result-list-item-template").html()
                        if (result['type'] == "member") {
                            result['icon'] = 'user'
                        }
                        else if (result['type'] == "party") {
                            result['icon'] = 'group'
                        }
                        else if (result['type'] == "tag") {
                            result['icon'] = 'tag'
                        }
                        var template = Handlebars.compile(source);
                        var html = template(result);
                        $('#search-gui-result-list').append(html)
                        addedElement = $('#search-gui-result-list').find("#" + result['type'] + result['id'])
                        addedElement.click(function () {
                            id = $(this).data('id')
                            name = $(this).data('name')
                            type = $(this).data('type')
                            icon = $(this).data('icon')
                            searchgui_add(id, name, type, icon)
                        })
                        addedElement.hover(function () {
                            $(this).find(".glyphicon-" + $(this).data('icon')).parent().toggleClass("alert-success")
                            $(this).find(".glyphicon-arrow-left").parent().toggleClass("hidden-badge")
                            $(this).find(".glyphicon-arrow-left").parent().toggleClass("alert-info")
                        })
                    }
                }
            });
        }
    })
});


function searchgui_add(id, name, type, icon) {

    var source = $("#search-gui-added-list-item-template").html()
    var template = Handlebars.compile(source);
    context = {'id': id, 'name': name, 'type': type, 'icon': icon}
    var html = template(context);
    $('#search-gui-' + type + '-added-list').append(html)
    addedElement = $('#search-gui-' + type + '-added-list').find("#" + type + id)
    addedElement.find(".glyphicon-remove").parent().click(function () {
        id = $(this).data('id')
        type = $(this).data('type')
        console.log()
        searchgui_remove(id, type)
    })
    addedElement.find(".glyphicon-remove").parent().hover(function () {
        $(this).toggleClass("alert-danger")
    })
    addedElement.hover(function () {
        $(this).find(".glyphicon-" + icon).parent().toggleClass("alert-success")
        $(this).find(".glyphicon-remove").parent().toggleClass("hidden-badge")
    })

    // clean-ups after adding //
    $('#searchgui-text-input').val('')

    searchgui_objects_visibility()


}

function searchgui_remove(id, type) {
    console.log("#" + type + id)
    $("#" + type + id).remove()
    searchgui_objects_visibility()

}

function searchgui_objects_visibility() {
    var tempScrollTop = $(window).scrollTop();
    searchTerms = {'member': [], 'party': [], 'tag': [], 'search_str': []}
    $(".result-info").each(function () {
        type = $(this).data('type')
        id = $(this).data('id')
        searchTerms[type].push(id)
    })
    console.log(searchTerms)
    var keysOfSearchTerms = Object.keys(searchTerms)
    console.log(keysOfSearchTerms)
    for (var i = 0; i < keysOfSearchTerms.length; i++) {
        if (searchTerms[keysOfSearchTerms[i]].length > 0) {
          $('#list-of-' + keysOfSearchTerms[i] + '-title').show()
        } else {
            $('#list-of-' + keysOfSearchTerms[i] + '-title').hide()
        }
    }

    var results_to_delete = $('#search-gui-result-list').children()
    for (var i = 0; i < results_to_delete.length; i++) {
        results_to_delete[i].remove()
    }
    if (searchTerms['tag'].length > 0 && searchTerms['search_str'].length > 0) {
        $('#searchgui-operator-input').show()
    } else {
        $('#searchgui-operator-input').hide()
    }
    $(window).scrollTop(tempScrollTop)
}