$(function() {
    var process_response = function(response_data) {
        if (!response_data || !response_data.error) {
            return true;
        }
        $('#alert-dialog-message').text(response_data.error.replace('\n', '<br>'));
        $('#alert-dialog').modal('show');
        return false;
    };
    
    var add_folder = function(folder_name) {
        $.ajax({
            url: '{% url "file_dispatcher" %}',
            type: 'POST',
            data: {
                filename: folder_name,
                location: $('#location').val(),
                action: 'mkdir'
            },
            dataType: 'json',
            success: function(response_data) {
                process_response(response_data);
                $('#folderadd-form').modal('hide');
            }
        });
    }
    
    var remove_item = function(action_type, item_name, force) {
        $.ajax({
            url: '{% url "file_dispatcher" %}',
            type: 'POST',
            data: {
                filename: item_name,
                location: $('#location').val(),
                action: action_type,
                force: force
            },
            dataType: 'json',
            success: function(response_data) {
                if (process_response(response_data)) {
                    location.reload(true);
                }
            }
        });
    };
    
    var update_description = function(name, hash, description) {
	$.ajax({
            url: '{% url "file_dispatcher" %}',
            type: 'POST',
            data: {
                filename: name,
		description: description,
                location: $('#location').val(),
                hashsum: hash,
                action: 'description'
            },
            dataType: 'json',
            success: function(response_data) {
                if (process_response(response_data)) {
                    location.reload(true);
                }
            }
        });
    };
    
    var toggle_replication = function(control) {
        $.ajax({
            url: '{% url "file_dispatcher" %}',
            type: 'POST',
            data: {
                filename: control.attr('data-itemname'),
                location: $('#location').val(),
                action: 'replication',
                hashsum: control.attr('data-hashsum'),
                replicate: control.hasClass('btn-danger') ? 'true' : ''
            },
            dataType: 'json',
            success: function(response_data) {
                if (process_response(response_data)) {
                    location.reload(true);
                }
            }
        });
    };
    
    $('#alert-dialog, #fileupload-form, #mv-form, #remove-form, #folderadd-form').modal({
        show: false,
        keyboard: true
    });
    
    $('#filepath').fileupload({
        dataType: 'json',
        add: function (event, data) {
            if (data.files.length < 1) {
                return;
            }
            $('#filepath').fileupload(
                'option',
                {
                    url: '{% url "file_dispatcher" %}',
                    formData: function() {
                        var values = [
                            {
                                name: 'action',
                                value: 'add'
                            },
                            {
                                name: 'filename',
                                value: data.files[0].name.toLowerCase()
                            }
                        ];
                        $('#filedescription, #location').each(function() {
                            var value = $(this).val();
                            if (value) {
                                values.push({
                                    name: $(this).attr('name'),
                                    value: value
                                });
                            }
                        });
                        return values;
                    }
                }
            );
            $('#fileupload').click(function() {
                $('#fileupload').hide();
                $('#progressbar-container').show();
                data.submit()
                    .success(function(result) { process_response(result); })
                    .error(function() { process_response({error: "error sending upload request to the web server"}); });
            });
            $('#filepath').hide();
            $('#filelabel').text(data.files[0].name.toLowerCase());
            $('#fileupload, #filelabel').show();
        },
        progress: function (event, data) {
            $('div.progressbar').css({width: parseInt(data.loaded / data.total * 100, 10) + '%'});
        },
        done: function (event, data) {
            $('div.progressbar').css({width: '100%'});
            setTimeout(function() {
                $('#fileupload-form').modal('hide');
            }, 1000);
        }
    });
    
    $('#fileadd').click(function() {
        $('#fileupload-form').modal('show');
    });
    
    $('#folderadd').click(function() {
        $('#foldername').val('');
        $('#folderadd-form').modal('show');
    });
    
    $('#folderadd-button').click(function() {
        var name = $(this).val();
        if (name) {
            add_folder($('#foldername').val());
        }
    });

    $('#foldername').keypress(function(e) {
        var name = $(this).val();
        if (e.which == 13 && name) {
            add_folder(name);
        }
    });
    
    $('#cancel-remove-button').click(function() {
        $('#remove-form').modal('hide');
    });
    
    $('#alert-dialog-close-button').click(function() {
        $('#alert-dialog').modal('hide');
    });
    
    $('#cancel-mv-button').click(function() {
        $('#mv-form').modal('hide');
    });
    
    $('td.remove > i').click(function() {
        var item_type = $(this).attr('data-itemtype');
        var item_name = $(this).attr('data-itemname');
        var action_map = {dir: 'rmdir', file: 'rm'};
        if ($(this).attr('data-empty') == 'True') {
            remove_item(action_map[item_type], item_name);
        }
        else {
            $('#remove-alert-message').text($(this).attr('data-message'));
            $('#remove-button').click(function() {
                $('#remove-form').modal('hide');
                remove_item(action_map[item_type], item_name, true);
            });
            $('#remove-form').modal('show');
        }
    });
    
    $('td.move > i').click(function() {
        var item_name = $(this).attr('data-itemname');
        $('#mv-filename').val(item_name);
        $('#mv-form-header').text("Move `" + item_name + "` to");
        $('#mv-form').modal('show');
    });
    
    $('td.toggle-versions > i').click(function() {
        var current_version_row = $(this).parent().parent();
        var filename = current_version_row.attr('data-filename');
        var previous_version_rows = $('tr.previous-version').filter(function() { return $(this).attr('data-filename') == filename; });
        
        previous_version_rows.toggle();
        if (previous_version_rows.is(':visible')) {
            $(this).addClass('icon-chevron-down').removeClass('icon-chevron-right');
        }
        else {
            $(this).addClass('icon-chevron-right').removeClass('icon-chevron-down');
        }
    });
    
    $('td.description > i').click(function() {
        var item_name = $(this).attr('data-itemname');
        var item_hash = $(this).attr('data-itemhash');
        
	$(this).next().replaceWith('<textarea>' + $(this).next().text() + '</textarea>');
	$(this).next().keypress(function(e) {
            var description = $(this).val();
            if (e.which == 13) {
		$(this).prop('readonly', true);
                update_description(item_name, item_hash, description);
            }
        });
    });
    
    $('.btn-replication').click(function() {
        toggle_replication($(this));
    });
    
    $('.css-treeview li i').click(function() {
        $(this).parent().children('ul').toggle();
        $(this).toggleClass('icon-folder-open').toggleClass('icon-folder-close');
    });

    $('.css-treeview li label').click(function() {
        $('#mv-button').removeClass('disabled');
        $('.css-treeview li label').removeClass('chosen-folder');
        $('.css-treeview li label i').remove();
        $(this).addClass('chosen-folder');
        $(this).append('<i class="icon-ok-sign"></i>');
    });

    $('#mv-button').click(function() {
        var chosen = $('.css-treeview li label.chosen-folder:lt(1)');
        $.ajax({
            url: '{% url "file_dispatcher" %}',
            type: 'POST',
            data: {
                filename: $('#mv-filename').val(),
                location: $('#location').val(),
                destination: chosen.attr('data-dest'),
                action: 'mv'
            },
            dataType: 'json',
            success: function(response_data) {
                if (process_response(response_data)) {
                    location.reload(true);
                }
            }
        });
    });

    $('#fileupload-form').on('shown', function() {
        $('#filedescription').focus();
    });
    
    $('#folderadd-form').on('shown', function() {
        $('#foldername').focus();
    });
    
    $('#fileupload-form, #folderadd-form').on('hidden', function() {
        location.reload(true);
    })
    
    $('#filebox-search-input').parent('form').submit(function() {
	return $.trim($('#filebox-search-input').val()) !== "";
    });
    
    $('#mv-form').on('hidden', function() {
        $('#mv-dirs-tbody').empty();
    });
});
