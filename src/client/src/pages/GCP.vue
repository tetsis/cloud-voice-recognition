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
    <div v-show="status == 'recognize'" class="row">
      <div class="col-md-12">
        <card :title="recognitionCard.title" :subTitle="recognitionCard.subTitle">
          <div class="text-center my-2">
            <b-spinner class="align-middle"></b-spinner>
            <p v-show="status == 'recognize'"><strong>This process takes a few minutues. <span class="text-danger">Don't reload this page. </span></strong></p>
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
            id="gcp-history-table"
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
        title: "Upload to GCS",
        subTitle: "The file must be in FLAC or WAV file format."
      },
      historyCard: {
        title: "History",
      },
      recognitionCard: {
        title: "Recognizing at Google Speech-to-Text...",
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
      jobName: '',
    };
  },
  mounted() {
    if (localStorage.getItem('gcpHistories')) {
      try {
        this.histories = JSON.parse(localStorage.getItem('gcpHistories'));
        this.myProvider();
      } catch(e) {
        localStorage.removeItem('gcpHistories');
      }
    }
    if (localStorage.gcpStatus) {
      this.status = localStorage.gcpStatus;
      if (this.status == 'complete') {
        this.status = 'upload';
      } 
    }
    if (localStorage.gcpObjectName) {
      this.objectName = localStorage.gcpObjectName;
    }
    if (localStorage.gcpJobName) {
      this.jobName = localStorage.gcpJobName;
    }
  },
  watch: {
    status(newStatus) {
      localStorage.gcpStatus = newStatus;
    },
    objectName(newObjectName) {
      localStorage.gcpObjectName = newObjectName;
    },
    jobName(newJobName) {
      localStorage.gcpJobName = newJobName;
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
        let jobName = value['jobName'];
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
      localStorage.setItem('gcpHistories', parsed);
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
        .post('/api/gcp/upload', formData, config)
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

      this.status = 'recognize';

      this.histories[this.objectName] = {
        'status': 'IN_PROGRESS',
        'language': this.selectedLanguage,
      };

      axios
        .post('/api/gcp/recognize', params)
        .then(response => {
          console.log('success');

          let data = response.data;
          this.transcript = data['transcript'];

          this.histories[this.objectName]['status'] = 'COMPLETED';
          this.histories[this.objectName]['transcript'] = this.transcript;
          this.saveHistories();
          this.notifyVue('top', 'right', 'success', 'Recognition completed')

          this.status = 'complete';
        })
        .catch(response => {
          this.status = 'upload';
          this.notifyVue('top', 'right', 'danger', 'Failed to recognize')
          console.log('failed');
        })
    },
  }
};
</script>
<style>
</style>