<template>
  <div>

    <!--Card-->
    <div v-show="status == 'upload'" class="row">
      <div class="col-md-12">
        <card :title="card.title" :subTitle="card.subTitle">
          <div class="row">
            <div class="col-md-8">
              <div>
                <!-- Styled -->
                <b-form-file
                  v-model="file"
                  :state="Boolean(file)"
                  placeholder="Choose a file or drop it here..."
                  drop-placeholder="Drop file here..."
                ></b-form-file>
                <div class="mt-3">Selected file: {{ file ? file.name : '' }}</div>
              </div>
            </div>
            <div class="col-md-4">
              <b-form-group
                id="fieldset-horizontal"
                label-cols-sm="4"
                label-cols-lg="3"
                label="Language"
                label-for="input-horizontal"
              >
                <b-form-select v-model="selectedLanguage" :options="optionsLanguage"></b-form-select>
              </b-form-group>
            </div>
          </div>
          <div class="text-center">
            <p-button type="info"
                      v-bind:disabled="isUpload"
                      round
                      @click.native.prevent="updateFile">
                        <span v-show="!isUpload">Upload voice file</span>
                        <span v-show="isUpload">
                          <b-spinner type="grow"></b-spinner>
                          Uploading...
                        </span>
            </p-button>
          </div>
        </card>
      </div>
    </div>

    <!--Card-->
    <div v-show="status == 'start' || status == 'recognize'" class="row">
      <div class="col-md-12">
        <card :title="recognitionCard.title" :subTitle="recognitionCard.subTitle">
          <div class="text-center my-2">
            <b-spinner class="align-middle"></b-spinner>
            <p v-show="status == 'start'"><strong>Starting recognition...</strong></p>
            <p v-show="status == 'recognize'"><strong>This process takes a few minutues.</strong></p>
          </div>
        </card>
      </div>
    </div>

    <!--Card-->
    <div v-show="status == 'complete'" class="row">
      <div class="col-md-12">
        <card :title="resultCard.title" :subTitle="resultCard.subTitle">
          <div class="text-center my-2">
            <p>{{ transcript }}</p>
          </div>
          <div class="text-center">
            <p-button type="info"
                      round
                      @click.native.prevent="backToUpload">
                        <span>Back to upload</span>
            </p-button>
          </div>
        </card>
      </div>
    </div>

    <!--Card-->
    <div class="row">
      <div class="col-md-12">
        <card :title="historyCard.title" :subTitle="historyCard.subTitle">
          <div>
          <b-table
            ref="historyTable"
            id="azure-history-table"
            :busy="isBusy"
            :items="myProvider"
          >
          </b-table>
          </div>
        </card>
      </div>
    </div>

  </div>
</template>

<script>
import { StatsCard } from "@/components/index";
import NotificationTemplate from './Notifications/NotificationTemplate';
import axios from 'axios';
export default {
  components: {
    StatsCard,
  },
  data() {
    return {
      selectedLanguage: 'ja-JP',
      optionsLanguage: [
        { value: 'ja-JP', text: 'ja-JP (Japanese)'},
        { value: 'en-US', text: 'en-US (English)'},
      ],
      histories: {},
      getVoiceTextInterval: null,
      transcript: '',
      isBusy: false,
      card: {
        title: "Upload to Blob Storage",
        subTitle: "The file must be in WAV or MP3 file format. MP3 file is converted to WAV automatically."
      },
      historyCard: {
        title: "History",
      },
      recognitionCard: {
        title: "Recognizing at Azure Speech Service...",
        subTitle: ""
      },
      resultCard: {
        title: "Recognition result",
        subTitle: ""
      },
      file: null,
      isUpload: false,
      status: 'upload',
      objectName: '',
      transcriptionId: '',
    };
  },
  mounted() {
    if (localStorage.getItem('azureHistories')) {
      try {
        this.histories = JSON.parse(localStorage.getItem('azureHistories'));
        this.myProvider();
      } catch(e) {
        localStorage.removeItem('azureHistories');
      }
    }
    if (localStorage.azureStatus) {
      this.status = localStorage.azureStatus;
      if (this.status == 'complete') {
        this.status = 'upload';
      } 
      if (this.status == 'recognize') {
        this.getVoiceTextInterval = setInterval(() => {
          this.getVoiceText()
        }, 5000);
      }
    }
    if (localStorage.azureObjectName) {
      this.objectName = localStorage.azureObjectName;
    }
    if (localStorage.azureTranscriptionId) {
      this.transcriptionId = localStorage.azureTranscriptionId;
    }
  },
  watch: {
    status(newStatus) {
      localStorage.azureStatus = newStatus;
    },
    objectName(newObjectName) {
      localStorage.azureObjectName = newObjectName;
    },
    transcriptionId(newTranscriptionId) {
      localStorage.azureTranscriptionId = newTranscriptionId;
    }
  },
  methods: {
    backToUpload() {
      this.status = 'upload';
    },
    myProvider() {
      let items = []
      for (let [key, value] of Object.entries(this.histories)) {
        let objectName = key;
        let transcriptionId = value['transcriptionId'];
        let status = value['status'];
        let language = value['language'];
        let transcript = value['transcript'];
        items.unshift({
          objectName: objectName,
          status: status,
          language: language,
          transcript: transcript
        })
      }
      return items || []
    },
    saveHistories() {
      const parsed = JSON.stringify(this.histories);
      localStorage.setItem('azureHistories', parsed);
      this.$refs.historyTable.refresh()
    },
    notifyVue(verticalAlign, horizontalAlign, type, title) {
      this.$notify({
        title: title,
        horizontalAlign: horizontalAlign,
        verticalAlign: verticalAlign,
        type: type
      });
    },
    updateFile() {
      let formData = new FormData();
      let config = {
        headers: {
          'content-type': 'multipart/form-data'
        }
      };
      formData.append('audio', this.file);
      this.isUpload = true;
      axios
        .post('/api/azure/upload', formData, config)
        .then(response => {
          this.isUpload = false;
          this.file = null;

          let data = response.data;
          this.objectName = data['object_name'];
          this.sampleRateHertz = data['sample_rate_hertz'];
          this.audioChannelCount = data['audio_channel_count'];
          console.log(this.objectName);

          // localStorageに保存
          this.histories[this.objectName] = {};
          this.saveHistories();

          console.log('success');
          this.notifyVue('top', 'right', 'success', 'Upload successful')

          this.recognizeVoice();
        })
        .catch(response => {
          this.isUpload = false;
          this.file = null;
          console.log('failed');
          this.notifyVue('top', 'right', 'danger', 'Failed to upload')
        })
    },
    recognizeVoice() {
      let params = new URLSearchParams();
      params.append('object_name', this.objectName);
      params.append('language', this.selectedLanguage);
      params.append('sample_rate_hertz', this.sampleRateHertz);
      params.append('audio_channel_count', this.audioChannelCount);
      this.recognitionCard.subTitle = this.objectName;
      this.resultCard.subTitle = this.objectName;

      this.status = 'start';

      this.histories[this.objectName] = {
        'language': this.selectedLanguage,
      };

      axios
        .post('/api/azure/recognize', params)
        .then(response => {
          console.log('success');

          let data = response.data;
          this.transcriptionId = data['transcription_id'];
          this.histories[this.objectName]['transcriptionId'] = this.transcriptionId;
          this.saveHistories();

          console.log(this.transcriptionId);
          this.notifyVue('top', 'right', 'success', 'Start recognition process')

          this.status = 'recognize';
          this.getVoiceTextInterval = setInterval(() => {
            this.getVoiceText()
          }, 5000);
        })
        .catch(response => {
          this.status = 'upload';
          this.notifyVue('top', 'right', 'danger', 'Failed to start recognition process')
          console.log('failed');
        })
    },
    getVoiceText() {
      this.status = 'recognize';
      let config = {
        params: {
            transcription_id: this.transcriptionId
          }
      };
      axios
        .get('/api/azure/text', config)
        .then(response => {
          console.log('success');

          let data = response.data;
          let status = data['status'];
          console.log(status);

          this.histories[this.objectName]['status'] = status;
          this.saveHistories();

          if (status == 'Succeeded') {
            console.log('COMPLETED');

            this.transcript = data['transcript'];
            console.log(this.transcript);

            this.histories[this.objectName]['transcript'] = this.transcript;
            this.saveHistories();

            clearInterval(this.getVoiceTextInterval);
            this.notifyVue('top', 'right', 'success', 'Recognition completed')
            this.status = 'complete';
          }
        })
        .catch(response => {
          this.status = 'upload';
          console.log('failed');
          clearInterval(this.getVoiceTextInterval);
        })
    },
  }
};
</script>
<style>
</style>